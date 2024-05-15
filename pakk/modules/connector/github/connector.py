from __future__ import annotations

import logging
import os
from multiprocessing.pool import ThreadPool
from threading import Lock

from pakk.helper.progress import execute_process_and_display_progress
import pytz
from github import Github
from github.ContentFile import ContentFile
from github.Organization import Organization
from github.PaginatedList import PaginatedList
from github.Repository import Repository
from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TimeElapsedColumn

from pakk.config.main_cfg import MainConfig
from pakk.modules.connector.base import Connector
from pakk.modules.connector.base import PakkageCollection
from pakk.modules.connector.cache import CachedRepository
from pakk.modules.connector.cache import CachedTag
from pakk.modules.connector.github.config import GithubConfig
from pakk.pakkage.core import Pakkage
from pakk.pakkage.core import PakkageVersions

logger = logging.getLogger(__name__)


class GithubConnector(Connector):
    CONFIG_CLS = GithubConfig

    def __init__(self, pakkages: PakkageCollection, **kwargs):
        super().__init__(pakkages, **kwargs)
        self.config = GithubConfig.get_config()

        self._token = self.config.private_token.value

        # TODO: Catch connection exceptions
        self._github = Github(self._token)

    def get_organization(self, name: str) -> Organization:
        return self._github.get_organization(name)

    def get_repos_of_organization(self, organization: Organization) -> PaginatedList[Repository]:
        return organization.get_repos()

    def get_repo(self, name: str) -> Repository:
        return self._github.get_repo(name)

    def get_cache_dir_path(self):
        return self.config.cache_dir.value

    def get_repo_cache_file_path(self, repo: Repository) -> str:
        name = repo.full_name.replace("/", "_")
        return os.path.join(self.get_cache_dir_path(), name + ".json")

    def _get_cached_repo(
        self, repo: Repository, existing_cache_file: CachedRepository | None = None
    ) -> CachedRepository:

        existing_cache_file = existing_cache_file or CachedRepository()
        pakk_cfg_file_name = MainConfig.get_config().pakk_cfg_files[0]

        existing_cache_file.id = repo.full_name
        existing_cache_file.last_activity = repo.pushed_at

        # Get all tags, skip if the tag is already in the cache
        for tag in repo.get_tags():
            if tag.name in existing_cache_file.tags:
                logger.debug(f"Tag {tag.name} already in cache")
                continue

            commit = tag.commit
            if commit is None:
                continue

            # Check if the tag is a pakk version
            pakk_config_str = ""
            is_pakk_version = False
            try:
                # Get root directory contents
                contents: list[ContentFile] = repo.get_contents("", ref=tag.name)  # type: ignore
                file_exists = any(file.path == pakk_cfg_file_name for file in contents)
                if file_exists:
                    file_content: ContentFile = repo.get_contents(pakk_cfg_file_name, ref=tag.name)  # type: ignore
                    pakk_config_str = file_content.decoded_content.decode("utf-8")
                    is_pakk_version = True

                logger.debug(f"\t Added {tag.name} (pakk version: {is_pakk_version})")
            except Exception as e:
                logger.warning(f"Error checking file presence in tag {tag.name} of repo {repo.name}: {str(e)}")

            cached_tag = CachedTag()
            cached_tag.tag = tag.name
            cached_tag.commit = commit.sha
            cached_tag.last_activity = tag.commit.commit.committer.date
            cached_tag.pakk_config_str = pakk_config_str
            cached_tag.is_pakk_version = is_pakk_version

            existing_cache_file.tags[tag.name] = cached_tag

        return existing_cache_file

    def _update_cache(self):
        """Helper method to update the cached projects"""
        # Discovering on GitHub only works for known organizations
        org_names = self.config.cached_organizations.value
        num_workers = int(self.config.num_discover_workers.value)

        logger.info(f"Updating GitHub cache...")

        for org_name in org_names:
            # Find the organization
            org = self._github.get_organization(org_name)

            logger.debug(f"Updating cache for organization {org_name}:")

            # # List all repos in the organization
            # for repo in org.get_repos():

            def process_repo(repo: Repository):
                # Load the cached repository
                cache_file_path = self.get_repo_cache_file_path(repo)
                cache_file = CachedRepository.from_file(cache_file_path)

                repo_dt = repo.pushed_at
                if repo_dt.tzinfo is None:
                    repo_dt = pytz.utc.localize(repo_dt)

                if cache_file is not None and repo_dt <= cache_file.last_activity:
                    # Use cached repository
                    logger.debug(f"Using cached repository for {repo.name}")
                    return

                logger.debug(f"Updating cache for repo {repo.name}")

                cache_file = self._get_cached_repo(repo, cache_file)
                cache_file.write(cache_file_path)

            n_public = org.total_private_repos or 0
            n_private = org.public_repos or 0

            execute_process_and_display_progress(
                items=org.get_repos(),
                item_processing_callback=process_repo,
                num_workers=num_workers,
                item_count=n_public + n_private,
                message=f"Updating github cache for {org_name}",
            )

    def discover(self) -> PakkageCollection:
        discovered_pakkages = PakkageCollection()
        num_workers = int(self.config.num_discover_workers.value)
        logger.info("Discovering projects from GitHub")

        self._update_cache()
        repos = CachedRepository.from_directory(self.get_cache_dir_path())

        n_repos, n_tags, n_pakk = 0, 0, 0

        for repo in repos:
            n_repos += 1
            pakkage_versions = PakkageVersions()
            for tag in repo.tags.values():
                n_tags += 1
                if not tag.is_pakk_version:
                    continue

                n_pakk += 1
                pakkage_versions.available[tag.version] = tag.pakk_config

            if len(pakkage_versions.available) == 0:
                continue

            pakkage = Pakkage(pakkage_versions)
            discovered_pakkages[pakkage.id] = pakkage

        logger.info(f"Discovered {n_repos} repositories with {n_tags} tags, {n_pakk} pakk versions")

        return discovered_pakkages

        logger.info("Discovering projects from GitHub")
        logger.debug(f"Main group id: {main_group_id}")
        logger.debug(f"Including archived projects: {self.config.include_archived.value}")
        logger.debug(f"Using {num_workers} workers" if num_workers > 1 else None)

        main_group = self.gl.groups.get(main_group_id)
        projects = main_group.projects.list(iterator=True, get_all=True, include_subgroups=True)

        self.cached_projects.clear()

        include_archived = self.config.include_archived.value

        results = {
            "lock": Lock(),
            "projects": self.cached_projects,
            "cached": 0,
            "not cached": 0,
            "archived": 0,
            "pbar": None,
        }

        # self.print_info(f"Discovering {len(projects)} projects...")
        logger.debug(f"Looking at {len(projects)} projects...")

        filtered_group_projects = list(
            filter(lambda gp: not gp.attributes.get("archived") or include_archived, projects)
        )
        results["archived"] = len(projects) - len(filtered_group_projects)

        # with tqdm.tqdm(total=len(filtered_group_projects)) as pbar:
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ) as progress:
            pbar = progress.add_task("[cyan]Discovering projects", total=len(filtered_group_projects))

            results["pbar"] = pbar

            def append_result(cp, cached):
                # pbar.update(1)
                progress.update(pbar, advance=1)
                if cached:
                    results["cached"] += 1
                else:
                    results["not cached"] += 1

                self.cached_projects.append(cp)

            if num_workers > 1:

                def process(gp):
                    return CachedProject.from_project(self, gp)

                # with Pool(num_workers) as pool:
                with ThreadPool(num_workers) as pool:
                    for res in pool.imap_unordered(process, filtered_group_projects):
                        append_result(*res)

                pool.join()
            else:
                for gp in filtered_group_projects:
                    append_result(*CachedProject.from_project(self, gp))

        logger.debug(f"Finished loading {len(projects)} projects:")
        logger.debug(f"  {results['not cached']} loaded from gitlab api")
        logger.debug(f"  {results['cached']} loaded from cache")
        logger.debug(
            f"  {results['archived']} archived projects were skipped"
            if results["archived"] > 0
            else "No archived projects found"
        )

        dps = self.retrieve_discovered_pakkages()
        n_versions = 0
        for p_id, pakkage in dps.discovered_packages.items():
            n_versions += len(pakkage.versions.available)

        logger.info(f"Discovered {len(dps.discovered_packages)} pakk packages with {n_versions} versions")

        return dps

    # def fetch(self, pakkages: FetchedPakkages) -> FetchedPakkages:
    #     pakkages_to_fetch = pakkages.pakkages_to_fetch

    #     for pakkage in pakkages_to_fetch:
    #         self.checkout_target_version(pakkage)
    #         progress.update(pbar, advance=1, info=f"Fetching: {pakkage.name}")
    #         logger.info(f"Fetched {pakkage.name}.")
    #         pakkages.fetched(pakkage)


if __name__ == "__main__":

    pass
    # Authentication
    # "your_github_token"

    # token = "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"
    # g = Github(token)

    # # Parameters
    # org_name = "icampus-wildau"
    # repo_activity_threshold = datetime.timedelta(days=30)  # 30 days
    # tag_activity_threshold = datetime.timedelta(days=30)  # 30 days
    # file_name = "pakk.cfg"

    # # Find the organization
    # org = g.get_organization(org_name)

    # # List all repos in the organization
    # for repo in org.get_repos():

    #     # Print repo information
    #     print(f"Repo: {repo.name}")

    #     # Get the latest activity on the repository
    #     repo_latest_activity = repo.pushed_at
    #     current_time = datetime.datetime.now(timezone.utc)
    #     if True or current_time - repo_latest_activity > repo_activity_threshold:
    #         # Get all tags of the repository
    #         for tag in repo.get_tags():

    #             print(f"Repo {repo.name}: Tag {tag.name}")

    #             # Get the commit associated with the tag
    #             commit = tag.commit

    #             if True or current_time - commit.commit.committer.date > tag_activity_threshold:
    #                 try:
    #                     # Check if the file exists at the tag
    #                     contents = repo.get_contents("", ref=tag.name)  # Get root directory contents
    #                     # print(f"Contents of tag {tag.name}: {contents}")
    #                     file_exists = any(file.path == file_name for file in contents)
    #                     if file_exists:
    #                         # Fetch the file from the tag
    #                         file_content = repo.get_contents(file_name, ref=tag.name)
    #                         print(f"File content from {tag.name}: {file_content.decoded_content.decode('utf-8')}")
    #                     else:
    #                         print(f"File {file_name} does not exist in tag {tag.name} of repo {repo.name}")
    #                 except Exception as e:
    #                     print(f"Error checking file presence in tag {tag.name} of repo {repo.name}: {str(e)}")
