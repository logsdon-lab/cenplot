import sys
import os
import argparse
import multiprocessing

import polars as pl

from typing import Iterable
from concurrent.futures import ProcessPoolExecutor

from cenplot import (
    plot_one_cen,
    merge_plots,
    read_one_cen_tracks,
    Track,
    SinglePlotSettings,
)


def get_inputs(
    args: argparse.Namespace,
) -> list[tuple[list[Track], str, str, SinglePlotSettings]]:
    all_chroms: Iterable[str] = [line.strip() for line in args.chroms.readlines()]

    inputs = []
    tracks_settings = [
        read_one_cen_tracks(args.input_track, chrom=chrom) for chrom in all_chroms
    ]
    xmin_all, xmax_all = sys.maxsize, 0
    if args.share_xlim:
        for _, settings in tracks_settings:
            if settings.xlim:
                xmin, xmax = settings.xlim
                xmin_all = min(xmin_all, xmin)
                xmax_all = max(xmax_all, xmax)

    for chrom in all_chroms:
        tracks_summary, plot_settings = read_one_cen_tracks(
            args.input_track, chrom=chrom
        )
        if args.share_xlim:
            plot_settings.xlim = (xmin_all, xmax_all)

        inputs.append(
            (
                [
                    Track(
                        trk.title,
                        trk.pos,
                        trk.opt,
                        trk.prop,
                        trk.data.filter(pl.col("chrom") == chrom),
                        trk.options,
                    )
                    for trk in tracks_summary.tracks
                ],
                args.outdir,
                chrom,
                plot_settings,
            )
        )
    return inputs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-t",
        "--input_track",
        required=True,
        type=str,
        help=(
            "TOML file with headerless BED files to plot. "
            "Specify under tracks the following fields: {name, position, type, proportion, path, or options}."
        ),
    )
    ap.add_argument(
        "-c",
        "--chroms",
        type=argparse.FileType("rt"),
        help="Names to plot in this order. Corresponds to 1st col in BED files.",
        default=None,
    )
    ap.add_argument(
        "-d",
        "--outdir",
        help="Output dir to plot multiple separate figures.",
        type=str,
        default=".",
    )
    ap.add_argument(
        "-o",
        "--outfile",
        help="Output file merging all figures. Either pdf of png.",
        type=str,
        default=None,
    )
    ap.add_argument("--share_xlim", help="Share x-axis limits.", action="store_true")

    ap.add_argument("-p", "--processes", type=int, default=4, help="Processes to run.")
    args = ap.parse_args()

    tracks = get_inputs(args)

    os.makedirs(args.outdir, exist_ok=True)
    if args.processes == 1:
        plots = [plot_one_cen(*track) for track in tracks]
    else:
        with ProcessPoolExecutor(
            max_workers=args.processes, mp_context=multiprocessing.get_context("spawn")
        ) as pool:
            plots = pool.map(plot_one_cen, *zip(*tracks))  # type: ignore[assignment]

    if args.outfile:
        merge_plots(plots, args.outfile)


if __name__ == "__main__":
    raise SystemExit(main())
