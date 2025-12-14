import logging
from datetime import datetime
import json

DIALOG_STEP_ENDED = ":stop:"


LOGMARKER_TIMING = "<<<TIMING>>>"
LOGMARKER_DIALOGUE = "<<<DIALOGUE>>>"
LOGMARKER_TESTING_START = "<<<TESTING STARTED>>>"
LOGMARKER_TESTING_END = "<<<TESTING ENDED>>>"
LOGMARKER_TESTING_END_ERROR = "<<<TESTING ENDED ERROR>>>"
LOGMARKER_AI = "<<<AI>>>"


def remove_empty_lines(text: str) -> str:
    return "\n".join([line for line in text.split("\n") if line.strip()])


class LogAi:

    def __init__(self, message: str) -> None:
        self.message = message

    def __repr__(self) -> str:
        return f"{LOGMARKER_AI} {self.message}"


class LogAiDialogStart:

    def __repr__(self):
        return f"""{LOGMARKER_AI} DIALOG START ---------------------------------------------------------------
----------------------------------------------------------------------------"""


class LogAiUserMessage:

    def __init__(self, message: str) -> None:
        self.message = message

    def __repr__(self) -> str:
        return f"{LOGMARKER_AI} USER MESSAGE:\n{self.message}"


class LogAiAgentResponse:

    def __init__(self, agent_name: str, response: str) -> None:
        self.agent_name = agent_name
        self.response = response

    def __repr__(self) -> str:
        return f"{LOGMARKER_AI} AGENT RESPONSE FROM '{self.agent_name}':\n{self.response}"


class LogTiming:

    def __init__(self, event: str) -> None:
        self.event = event

    def __repr__(self) -> str:
        return f"{LOGMARKER_TIMING} {self.event}"


class TimingLogger:

    def __init__(self, event: str) -> None:
        self.event = event
        self.time = datetime.now()

    def __enter__(self):
        logging.info(LogTiming(f"{self.event}:start"))
        self.time = datetime.now()

    def __exit__(self, exc_type, exc_value, traceback):
        elapsed_time = datetime.now() - self.time
        if exc_type:
            logging.error(LogTiming(f"{self.event}:end_with_error ({exc_type.__name__}: {exc_value}) (elapsed time: {elapsed_time})"))
        else:
            logging.info(LogTiming(f"{self.event}:end (elapsed time: {elapsed_time})"))


class TimingLogger:

    """
    A context manager for logging the timing of events. This class is optimized for "structured" logging,
    which means that it will log the start and end of an event with a structured format for later analysis
    of the logs.
    """

    def __init__(self, event: str) -> None:
        self.event = event
        self.time = datetime.now()

    def __enter__(self):
        logging.info(LogTiming(f"{self.event}:start"))
        self.time = datetime.now()

    def __exit__(self, exc_type, exc_value, traceback):
        elapsed_time = datetime.now() - self.time
        if exc_type:
            logging.error(LogTiming(f"{self.event}:end_with_error ({exc_type.__name__}: {exc_value}) (elapsed time: {elapsed_time})"))
        else:
            logging.info(LogTiming(f"{self.event}:end (elapsed time: {elapsed_time})"))


class Timing:

    """
    A context manager for logging the timing of events. This class logs in a more human-readable format,
    which is useful for quick debugging and understanding the flow of the application. It does not log the start
    of the event, only the end with the elapsed time.
    """

    def __init__(self, event: str) -> None:
        self.event = event
        self.time = datetime.now()

    def __enter__(self):
        self.time = datetime.now()

    def __exit__(self, exc_type, exc_value, traceback):
        elapsed_time = datetime.now() - self.time
        if exc_type:
            logging.error(LogTiming(f"{self.event}: ended with error ({exc_type.__name__}: {exc_value}), elapsed time: {elapsed_time}"))
        else:
            logging.info(LogTiming(f"{self.event}: ended, elapsed time: {elapsed_time}"))




class TestingSession:

    def __init__(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.session_id = f"session_{timestamp}"

    def __enter__(self):
        logging.info(f"{LOGMARKER_TESTING_START} {self.session_id}")

    def __exit__(self, exc_type, exc_value, traceback):

        if exc_type:
            details = {"session_id": self.session_id, "error_type": exc_type.__name__, "error_message": str(exc_value)}
            logging.info(f"{LOGMARKER_TESTING_END_ERROR} {json.dumps(details)}")
        else:
            logging.info(f"{LOGMARKER_TESTING_END} {self.session_id}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("--------------------")
    with TestingSession():
        with TimingLogger("test_timing"):
            print("doing stuff...")

    print("--------------------")
    with TestingSession():
        with TimingLogger("test_timing"):
            try:
                print("doing stuff...")
                raise RuntimeError("test error")
            except RuntimeError as e:
                logging.error(f"Error: {e}")
                # raise e
