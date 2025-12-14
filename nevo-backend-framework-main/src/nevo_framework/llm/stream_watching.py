import asyncio
import logging
import logging.config
from datetime import datetime
from typing import Awaitable, Callable

from pydantic import BaseModel

from nevo_framework.llm.llm_tools import TimedWebElementMessage


class SentenceWatcher:

    SENTENCE_TERMINALS = [". ", "? ", "! ", ": ", ".\n", "?\n", "!\n", ":\n", ","]
    END_OF_STREAM = "::::::::::::::::::::::::::::EOS::::::::::::::::::::::::::::"

    def __init__(
        self,
        sentence_callback: Callable[[str, list[str], asyncio.Queue], Awaitable[bool]],
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        terminals: str | None = None,
    ):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.buffer = ""
        self.sentences = []
        self.callback = sentence_callback
        if terminals:
            self.terminals = terminals
        else:
            self.terminals = SentenceWatcher.SENTENCE_TERMINALS

    async def watch_stream(self):
        while True:
            try:
                text_chunk = await asyncio.wait_for(self.input_queue.get(), timeout=60)
            except asyncio.TimeoutError:
                logging.error("SentenceWatcher: Timeout waiting for input chunk.")
                break
            if text_chunk == SentenceWatcher.END_OF_STREAM:
                await self._end_stream()
                break
            else:
                keep_watching = await self._handle_text_chunk(text_chunk)
                if not keep_watching:
                    await self._end_stream()
                    break

    async def _handle_text_chunk(self, chunk: str) -> bool:
        self.buffer += chunk
        for terminal in SentenceWatcher.SENTENCE_TERMINALS:
            if terminal in self.buffer:
                head, tail = self.buffer.split(terminal)
                self.buffer = tail
                sentence = head + terminal
                self.sentences.append(sentence)
                try:
                    keep_watching = await self.callback(sentence, self.sentences, self.output_queue)
                    return keep_watching
                except Exception as e:
                    logging.error(f"SentenceWatcher - error in callback: {e}")
                break
        return True  # keep watching

    async def _end_stream(self):
        if self.buffer:
            sentence = self.buffer
            await self.callback(sentence, self.sentences, self.output_queue)
        self.output_queue.put_nowait(SentenceWatcher.END_OF_STREAM)
        self.buffer = ""
        self.sentences = []


async def watch_timed_message_queue(timed_message_queue: asyncio.Queue, output_queue: asyncio.Queue):
    t_start = datetime.now()
    while True:
        try:
            message = await asyncio.wait_for(timed_message_queue.get(), timeout=180)
        except asyncio.TimeoutError:
            logging.error("Output queue: Timeout waiting for timed messages.")
            break
        if message == SentenceWatcher.END_OF_STREAM:
            break
        elif isinstance(message, BaseModel):
            logging.debug(f"Output queue, no timing: {message}")
            output_queue.put_nowait(message)
        # You must pass the TimedWebElementMessage(s) to the queue inside a list, even if it's a single object
        # this enables us to pass one or more sequentially timed messaged easily into the queue
        elif isinstance(message, TimedWebElementMessage):
            current_time = datetime.now() - t_start
            if current_time.total_seconds() > message.time_delta:
                logging.warning(f"Timed message is late: {message.message}")
                output_queue.put_nowait(message.message)
            else:
                delay = message.time_delta - current_time.total_seconds()
                logging.info(f"Output queue: waiting for {delay} seconds to send message: {message.message}")
                await asyncio.sleep(delay)
                output_queue.put_nowait(message.message)
                logging.info(f"{datetime.now()} Output queue, {message}, current time is: {datetime.now() - t_start}")
        else:
            logging.error(
                f"Timed message queue - unknown message type, expecting BaseModel or list[TimedWebElementMessage]: {type(message)} / {message}"
            )


class TestMessage(BaseModel):
    content: str
    sentence_count: int


class TestSentenceAction:

    def __init__(self, sentence_limit: int | None = None):
        self.sentence_count = 0
        self.sentence_limit = sentence_limit

    async def print_sentence(self, sentence: str, sentences: list[str], output_queue: asyncio.Queue) -> bool:
        message = TestMessage(content=sentence, sentence_count=self.sentence_count)
        output_queue.put_nowait(TimedWebElementMessage(message=message, time_delta=1.0 + 2.0 * self.sentence_count))
        self.sentence_count += 1
        if self.sentence_limit and self.sentence_count == self.sentence_limit:
            return False
        return True


async def main():
    logging.basicConfig(level=logging.DEBUG)

    # AI generated text
    test_text = """Dear Sir/Madam! 
    I am writing to complain about the service I have received from your company. I am very disappointed with the way I have been treated.
    I have been a loyal customer of your company for many years and I have always been satisfied with the service I have received. 
    However, recently I have had a number of problems with your company:
    First of all, I have had a number of problems with the products I have purchased from your company. 
    The products have been of poor quality and have not worked properly. 
    In addition, I have had a number of problems with the delivery of the products. 
    The products have been delivered late and in some cases they have not been delivered at all! 
    I have also had a number of problems with the customer service I have received from your company. 
    The customer service representatives I have spoken to have been rude and unhelpful. They have not been willing to listen to my complaints and have not been willing to help me resolve the problems I have had. I am very disappointed with the service I have received from your company and I would like to make a formal complaint. I would like to request a full refund for the products I have purchased from your company. I would also like to request compensation for the problems I have had with the delivery of the products. I would like to request that you take action to improve the customer service I have received from your company. I look forward to hearing from you soon. 
    
    Yours faithfully, 
    John Smith
    """

    timed_message_queue = asyncio.Queue()
    output_queue = asyncio.Queue()
    chunk_queue = asyncio.Queue()
    callback = TestSentenceAction(sentence_limit=1000000)
    stream_watcher = SentenceWatcher(
        sentence_callback=callback.print_sentence, input_queue=chunk_queue, output_queue=timed_message_queue
    )
    stream_watcher_task = asyncio.create_task(stream_watcher.watch_stream())
    timed_queue_task = asyncio.create_task(
        watch_timed_message_queue(timed_message_queue=timed_message_queue, output_queue=output_queue)
    )
    chunk_len = 11
    for i in range(0, len(test_text), chunk_len):
        chunk = test_text[i : i + chunk_len]
        chunk_queue.put_nowait(chunk)
        await asyncio.sleep(0.01)
    chunk_queue.put_nowait(SentenceWatcher.END_OF_STREAM)
    await asyncio.gather(stream_watcher_task, timed_queue_task)
    

if __name__ == "__main__":
    asyncio.run(main())
