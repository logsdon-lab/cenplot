import os
import sys
import tomllib
from typing import Any, Generator

import polars as pl

from .bed9 import read_bed9
from .bed_identity import read_bed_identity
from .bed_label import read_bed_label
from .bed_hor import read_bed_hor
from ..track import Track, TrackOption, TrackPosition


def read_one_track_info(
    track: dict[str, Any], *, chrom: str | None = None
) -> Generator[Track, None, None]:
    prop = track.get("proportion", 0.0)
    name = track.get("name")
    pos = track.get("position")
    opt = track.get("type")
    path: str | None = track.get("path")
    options: dict[str, Any] = track.get("options", {})

    if not name:
        raise ValueError(f"Name not provided for track ({track}).")

    try:
        track_pos = TrackPosition(pos)  # type: ignore[arg-type]
    except ValueError:
        print(
            f"Invalid plot position ({pos}) for {path}. Skipping.",
            file=sys.stderr,
        )
        return None
    try:
        track_opt = TrackOption(opt)  # type: ignore[arg-type]
    except ValueError:
        print(
            f"Invalid plot option ({opt}) for {path}. Skipping.",
            file=sys.stderr,
        )
        return None

    if not path:
        raise ValueError("Path to data required.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Data does not exist for track ({track})")

    if opt == TrackOption.HORSplit:
        mer_order = options.get("mer_order", "large")
        df_track = read_bed_hor(path, chrom=chrom, mer_order=mer_order)
        uniq_mers = df_track["mer"].unique()
        track_prop = prop / len(uniq_mers)
        if track_pos == TrackPosition.Overlap:
            print(
                f"Overlap not supported for {opt}. Using relative position.",
                file=sys.stderr,
            )

        for mer, df_mer_track in df_track.group_by(["mer"], maintain_order=True):
            mer = mer[0]
            # Add (mer) to name.
            # Disallow overlap.
            # Split proportion over uniq monomers.
            yield Track(
                f"{name} ({mer})",
                TrackPosition.Relative,
                TrackOption.HOR,
                track_prop,
                df_mer_track,
                options,
            )

        return None

    if opt == TrackOption.HOR:
        mer_order = options.get("mer_order", "large")
        df_track = read_bed_hor(path, chrom=chrom, mer_order=mer_order)
    elif opt == TrackOption.SelfIdent:
        df_track = read_bed_identity(path, chrom=chrom)
    elif opt == TrackOption.Value:
        df_track = read_bed9(path, chrom=chrom)
    else:
        df_track = read_bed_label(path, chrom=chrom)

    yield Track(name, track_pos, track_opt, prop, df_track, options)


def get_min_max_track(
    tracks: list[Track], typ: str, default_col: str = "chrom_st"
) -> tuple[Track, int]:
    track = None
    if typ == "min":
        pos = sys.maxsize
    else:
        pos = 0

    for trk in tracks:
        if trk.opt == TrackOption.SelfIdent:
            col = "x"
        else:
            col = default_col
        if typ == "min":
            trk_min = trk.data.filter(pl.col(col) > 0)[col].min()
            if trk_min < pos:
                track = trk
                pos = trk_min
        else:
            trk_max = trk.data[col].max()
            if trk_max > pos:
                track = trk
                pos = trk_max
    if not track:
        raise ValueError("No tracks.")
    return track, pos


def read_all_tracks(
    input_tracks: list[str], *, chrom: str | None = None
) -> tuple[list[Track], set[str], tuple[int, int]]:
    all_tracks = []
    chroms = set()
    for input_track in input_tracks:
        with open(input_track, "rb") as fh:
            tracks = tomllib.load(fh).get("tracks", [])
            for track_info in tracks:
                for track in read_one_track_info(track_info, chrom=chrom):
                    all_tracks.append(track)
                    chroms.update(track.data["chrom"])

    _, min_st_pos = get_min_max_track(all_tracks, typ="min")
    _, max_end_pos = get_min_max_track(all_tracks, typ="max", default_col="chrom_end")
    return all_tracks, chroms, (min_st_pos, max_end_pos)
