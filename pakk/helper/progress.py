from __future__ import annotations

from multiprocessing.pool import ThreadPool
from typing import Callable, Iterable, TypeVar

from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TimeElapsedColumn

T = TypeVar("T")


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
                total_items = len(items)
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
