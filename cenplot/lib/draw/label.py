from typing import Any
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle

from .utils import add_border, draw_uniq_entry_legend, format_ax
from ..track.types import Track, TrackPosition


def draw_label(
    ax: Axes,
    track: Track,
    *,
    zorder: float,
    legend_ax: Axes | None = None,
) -> None:
    hide_x = track.options.hide_x
    color = track.options.color
    alpha = track.options.alpha
    legend = track.options.legend
    border = track.options.border

    patch_options: dict[str, Any] = {"zorder": zorder}
    patch_options["alpha"] = alpha

    # Overlapping tracks should not cause the overlapped track to have their spines/ticks/ticklabels removed.
    if track.pos != TrackPosition.Overlap:
        spines = (
            ("right", "left", "top", "bottom") if hide_x else ("right", "left", "top")
        )
        yticks = True
    else:
        yticks = False
        spines = None
    format_ax(
        ax,
        xticks=hide_x,
        xticklabel_fontsize=track.options.fontsize,
        yticks=yticks,
        yticklabel_fontsize=track.options.fontsize,
        spines=spines,
    )

    ylim = ax.get_ylim()
    height = ylim[1] - ylim[0]

    for row in track.data.iter_rows(named=True):
        start = row["chrom_st"]
        end = row["chrom_end"]

        if row["name"] == "-" or not row["name"]:
            labels = {}
        else:
            labels = {"label": row["name"]}
        # Allow override.
        if color:
            patch_options["color"] = color
        elif "color" in row:
            patch_options["color"] = row["color"]

        rect = Rectangle(
            (start, 0),
            end + 1 - start,
            height,
            # No line width on each individual rect.
            lw=0,
            **labels,
            **patch_options,
        )
        ax.add_patch(rect)

    if border:
        # Ensure border on top with larger zorder.
        add_border(ax, height, zorder=zorder + 1.0)

    # Draw legend.
    if legend_ax and legend:
        draw_uniq_entry_legend(
            legend_ax,
            track,
            ref_ax=ax,
            ncols=track.options.legend_ncols,
            loc="center",
        )
