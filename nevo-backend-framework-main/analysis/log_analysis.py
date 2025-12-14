import re
from datetime import datetime
from typing import Iterable

import pandas as pd
import logging
import json

from nevo_framework.helpers.logging_helpers import (
    LOGMARKER_TIMING,
    LOGMARKER_TESTING_START,
    LOGMARKER_TESTING_END,
    LOGMARKER_TESTING_END_ERROR,
)

server_timestamp_pattern = re.compile(r"SERVER \[(.*?)\]")


def get_timing_data(logfile_path: str, discard_error_sessions: bool = True) -> pd.DataFrame:

    testing_session = None
    records = []
    sessions_with_errors = set()

    with open(logfile_path, "r") as logfile:
        for line_nbr, line in enumerate(logfile):
            if line.startswith("CLIENT") or line.startswith("SERVER"):
                if LOGMARKER_TESTING_START in line:
                    testing_session = line.split(LOGMARKER_TESTING_START)[1].strip()
                    print(f"Session start: {testing_session}")
                    continue
                elif LOGMARKER_TESTING_END in line:
                    assert testing_session == line.split(LOGMARKER_TESTING_END)[1].strip()
                    print(f"Session end: {testing_session}")
                    testing_session = None
                    continue
                elif LOGMARKER_TESTING_END_ERROR in line:
                    details = json.loads(line.split(LOGMARKER_TESTING_END_ERROR)[1].strip())
                    assert testing_session == details["session_id"]
                    print(f"Session end with error: {testing_session}")
                    testing_session = None
                    sessions_with_errors.add(details["session_id"])
                    continue
                elif LOGMARKER_TIMING in line:
                    if testing_session is None:
                        print(f"No testing session for <<<TIMING>>> event on line {line_nbr}, skipping.")
                        continue
                    timestamp_match = server_timestamp_pattern.search(line)
                    if timestamp_match:
                        timestamp_str = timestamp_match.group(1)
                        if "." in timestamp_str:  # due to a now fixed bug in the logger
                            timestamp_str = timestamp_str.split(".")[0]
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                        event = line.split(LOGMARKER_TIMING)[1].strip()
                        records.append(
                            {
                                "session": testing_session,
                                "timestamp": timestamp,
                                "event": event,
                                "log_line": line_nbr + 1,
                            }
                        )
    for record in records:
        record["session_error"] = record["session"] in sessions_with_errors

    df = pd.DataFrame(rec for rec in records if not (discard_error_sessions and rec["session_error"]))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by=["session", "timestamp"])
    return df


def timing_report(
    event_1: str, event_2: str, timing_data: pd.DataFrame, description: str = None, print_full_details: bool = False
) -> pd.DataFrame:
    """
    Analyze the timing between two events in the log data, and print a report.
    The report provides a breakdown by session and an overall summary.

    Args:
        event_1 (str): The first event name.
        event_2 (str): The second event name.
        timing_data (pd.DataFrame): The timing data.
        description (str): A description to print before the report.
        print_full_details (bool): If True, print the full details of the timing data. Otherwise, only print the summaries.

    Returns:
        pd.DataFrame: The timing data.
    """
    fltr = timing_data["event"].isin([event_1, event_2])
    records = []
    for session, group in timing_data.loc[fltr, :].groupby("session"):
        t = None
        first_event_line = None
        for _, row in group.iterrows():
            if row["event"] == event_1:
                t = row["timestamp"]
                first_event_line = row["log_line"]
            elif row["event"] == event_2 and t is not None:
                delta: pd.Timedelta = row["timestamp"] - t
                records.append(
                    {
                        "session": session,
                        "delta": delta.total_seconds(),
                        "first_event_line": first_event_line,
                        "second_event_line": row["log_line"],
                    }
                )
                t = None
    df_timing = pd.DataFrame(records).set_index("session")
    summary_by_session = df_timing.groupby("session").agg(
        mean=("delta", "mean"),
        min=("delta", "min"),
        max=("delta", "max"),
        count=("delta", "count"),
        median=("delta", "median"),
    )
    summary = df_timing.agg(
        mean=("delta", "mean"),
        min=("delta", "min"),
        max=("delta", "max"),
        count=("delta", "count"),
        median=("delta", "median"),
    )
    if description:
        print(description)
    print(f"{event_1} -> {event_2}")
    print(summary)
    print(summary_by_session)
    if print_full_details:
        print(df_timing)
    print()
    print()
    return df_timing
