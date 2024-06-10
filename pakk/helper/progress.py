from __future__ import annotations

from multiprocessing.pool import ThreadPool
from typing import Callable
from typing import Generic
from typing import Iterable
from typing import TypeVar

from rich.progress import BarColumn
from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TaskID
from rich.progress import TextColumn
from rich.progress import TimeElapsedColumn
from rich.progress import TimeRemainingColumn

from pakk.logger import console

T = TypeVar("T")

import logging

logger = logging.getLogger(__name__)


def execute_process_and_display_progress(
    items: Iterable[T],
    item_processing_callback: Callable[[T], None],
    num_workers: int = 1,
    item_count: int | None = None,
    message: str = "Updating cache",
) -> None:
    # with tqdm.tqdm(total=len(filtered_group_projects)) as pbar:
    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
    ) as progress:
        if item_count is not None:
            total_items = item_count
        else:
            try:
                total_items = len(items)  # type: ignore
            except TypeError:
                total_items = None

        pbar = progress.add_task(f"[cyan]{message}", total=total_items)

        if num_workers > 1:
            # with Pool(num_workers) as pool:
            with ThreadPool(num_workers) as pool:
                for res in pool.imap_unordered(item_processing_callback, items):
                    # append_result(*res)
                    progress.update(pbar, advance=1)

            pool.join()
        else:
            for gp in items:
                # append_result(*CachedProject.from_project(self, gp))  # type: ignore
                item_processing_callback(gp)
                progress.update(pbar, advance=1)


class TaskPbar:
    def __init__(
        self,
        progress: Progress,
        description: str,
        start: bool = True,
        total: int | None = None,
        completed: int = 0,
        visible: bool = True,
        **fields: str | int | float | bool | None,
    ):
        self.progress: Progress = progress
        self.id: TaskID = progress.add_task(
            description, start=start, total=total, completed=completed, visible=visible, **fields
        )
        self.free: bool = True

        self.fields = fields

    def update(
        self,
        *,
        total: int | None = None,
        completed: float | None = None,
        advance: float | None = None,
        description: str | None = None,
        visible: bool | None = None,
        refresh: bool = False,
        **fields: str | int | float | bool | None,
    ):
        self.fields = {**self.fields, **fields}
        self.progress.update(
            self.id,
            total=total,
            completed=completed,
            advance=advance,
            description=description,
            visible=visible,
            refresh=refresh,
            **fields,
        )


class ProgressManager(Generic[T]):
    def __init__(
        self,
        items: list[T],
        item_processing_callback: Callable[[T, TaskPbar], None],
        num_workers: int = 1,
        summary_description: str = "[blue]Fetching Total:",
        worker_description: str = "[cyan]Worker:",
        text_fields: list[str] = [],
    ):
        self.tasks: list[TaskPbar] = []

        self.summary_description: str = summary_description
        self.worker_description: str = worker_description
        self.num_workers: int = num_workers

        self._progress: Progress | None = None

        self.items: list[T] = items

        self.item_processing_callback = item_processing_callback

        self.text_fields: list[str] = text_fields

    def _get_text_columns(self) -> list[TextColumn]:
        return [TextColumn(f"{{task.fields[{field}]}}") for field in self.text_fields]

    def _acquire_next_free_task(self) -> TaskPbar:
        for task in self.tasks:
            if task.free:
                task.free = False
                return task

        raise Exception("No free task available.")

    def _release_task(self, task: TaskPbar):
        task.free = True

    def _process_item(self, item: T):

        # Get the next free task pbar
        task = self._acquire_next_free_task()

        # Call the item processing callback
        self.item_processing_callback(item, task)

        # Release the task pbar
        self._release_task(task)

    def execute(self):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            # TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            # TextColumn("{task.fields[pakkage]}"),
            # TextColumn("{task.fields[info]}"),
            *self._get_text_columns(),
            transient=True,
            console=console,
        ) as progress:
            self._progress = progress

            fields = {f: "" for f in self.text_fields}
            # summary_pbar = progress.add_task(self.summary_description, total=len(self.items), **fields)
            summary_pbar = TaskPbar(progress, self.summary_description, total=len(self.items), **fields)  # type: ignore

            # if self.num_workers >= 1:
            num_workers = max(1, self.num_workers)
            num_workers = min(num_workers, len(self.items))
            for i in range(num_workers):
                task = TaskPbar(progress, self.worker_description.format(i + 1), total=None, pakkage="", info="")
                self.tasks.append(task)
                # self._pbars.append(progress.add_task(f"[cyan]Worker{i + 1}:", total=None, pakkage="", info=""))
                # self._free_pbars.append(True)

            # Don't use multiprocessing.Pool since it will spawn new processes and not threads,
            # thus the data will not be shared.
            # See:
            # https://stackoverflow.com/questions/3033952/threading-pool-similar-to-the-multiprocessing-pool
            # https://stackoverflow.com/questions/52486811/how-to-properly-reference-to-instances-of-a-class-in-multiprocessing-pool-map
            # https://towardsdatascience.com/demystifying-python-multiprocessing-and-multithreading-9b62f9875a27
            with ThreadPool(num_workers) as pool:
                for res in pool.imap_unordered(self._process_item, self.items):
                    summary_pbar.update(advance=1, info="")
                    # progress.update(summary_pbar, advance=1, info="")
                    # if res is not None:
                    #     logger.info(f"Fetched {res.name}.")
                    # pakkages.fetched(res)
            pool.join()
            # else:
            #     self._pbars.append(progress.add_task(f"[cyan]Worker{1}:", total=None, pakkage="", info=""))
            #     self._free_pbars.append(True)

            #     for pakkage in pakkages_to_fetch:
            #         self.checkout_version(pakkage)
            #         progress.update(summary_pbar, advance=1, info=f"Fetching: {pakkage.name}")
            #         logger.info(f"Fetched {pakkage.name}.")
            #         # pakkages.fetched(pakkage)
