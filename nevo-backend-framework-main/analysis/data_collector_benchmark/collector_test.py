"""
This script tests the collector module. The testing is done by passing strings to the collector and checking
what information it captures as well as tracking how long it takes to capture this information
"""
import asyncio
import json
import itertools
import argparse
from dataclasses import dataclass
import time

import pandas as pd

from testing.simple_agents import FunctionCallingAgent
from analysis.data_collector_benchmark.create_collectors import create_openai_collectors


@dataclass
class Metrics:
    precision: float
    recall: float
    f1: float

def create_collectors(single_collector: bool=True, time_debug: bool=False) -> list[FunctionCallingAgent]:
    """Function that creates the collectors
    
    Args:
        single_collector (bool, optional): Whether to have only a single collector for all user info across the customer journey
        time_debug (bool, optional): Whether to print the time taken to collect the data; this is saved as the 
            .duration property in collector anyway, so it's not really necessary here

    Returns:
        list[FunctionCallingAgent]: A list of function calling agents
    """

    tools_list = create_openai_collectors()

    if single_collector:
        tools_list = list(itertools.chain(*tools_list))
        data_collectors = [
        FunctionCallingAgent(
            tools=tools_list, 
            model="gpt-4o-mini", 
            time_debug=time_debug, 
            name="General Collector"
            )
    ]
    else:
        collector_names = ["Host", "Product", "Sales"]
        data_collectors = [
            FunctionCallingAgent(
                tools=tools, 
                model="gpt-4o", 
                time_debug=time_debug, 
                name=collector_names[i]
                ) for i, tools in enumerate(tools_list)
        ]

    return data_collectors


async def get_response_async(user_message: str, data_collectors: list[FunctionCallingAgent]) -> list[str]:
    """Function which returns the collected data from the user message
    
    Args:
        user_message (str): The message from the user
        data_collectors (list[FunctionCallingAgent]): The list of data collectoring function calling agents

    Returns:
        list[str]: A list of strings containing the collected data
    """
    data_collector_coroutines = [
            collector(user_message) for collector in data_collectors
    ]
   
    data_collector_results = await asyncio.gather(*data_collector_coroutines)

    return data_collector_results

def load_test_examples(filepath: str) -> dict:
    """Function which loads a test example from the filepath and returns a dictionnry"""

    with open(filepath, "r") as file:
        examples = json.load(file)

    return examples

def compare_results(test_data: dict, generated_data: dict):
    """Function which compares the original data with the generated data"""

    for key in test_data.keys():
        if key != "message" and (test_data.get(key, False) or generated_data.get(key, False)):
            print(f"test_data: {test_data.get(key, False)}\t generated_data: {generated_data.get(key, False)}")


def calculate_metrics(test_values: list[str], generated_values: list[str], verbose: bool) -> Metrics:
    """Function which calculates the precision, recall and f1 score of the generated values

    Args:
        test_values (list[str]): These are the pieces of information that should have been extracted from the user message
        generated_values (list[str]): These are the pieces of information that were extracted from the user message
        verbose (bool): bool indicating whether to display test and generated values during testing

    Returns:
        Metrics: A dataclass containing the precision, recall and f1 score
    """

    print(f"test_values: {test_values}\t generated_values: {generated_values}") if verbose else ""
    tp = set(test_values).intersection(set(generated_values))
    fp = set(generated_values).difference(set(test_values))
    fn = set(test_values).difference(set(generated_values))

    precision = len(tp) / (len(tp) + len(fp)) if (len(tp) + len(fp)) > 0 else 0.0
    recall = len(tp) / (len(tp) + len(fn)) if (len(tp) + len(fn)) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return Metrics(
        precision=round(precision,2),
        recall=round(recall,2),
        f1=round(f1,2)
    )

def main():
    print("\n----- Testing the collector module -----\n")

    parser = argparse.ArgumentParser(description="Test the collector module")
    parser.add_argument('--single_collector', action='store_true', help='Use a single collector for all tools')
    parser.add_argument('--iters', type=int, default=1, help='Numbef of iterations of the tests to run to check for variability')
    parser.add_argument('--verbose', action='store_true', help='Whether to print all intermediate results or not')
    parser.add_argument('--output_filename', type=str, default="output.csv", help='Name of the output csv with results per run')

    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    run_data = {}
    test_examples = load_test_examples("src/tests/collector_test.json")

    for i in range(args.iters):
        print(f"Currently on iteration {i+1} of {args.iters}") if not args.verbose else ""
        avg_precision, avg_recall, avg_f1 = 0, 0, 0
        duration_times = []
        for example in test_examples:
            data_collectors = create_collectors(args.single_collector)
            flattened_collected_data = {}

            print(f"User message: {example.get('message', None)}") if args.verbose else ""
            ts = time.time()
            loop.run_until_complete(get_response_async(user_message=example.get("message"), data_collectors=data_collectors))
            print(f"Extra check: total aysnc time {time.time() - ts:.2f}s ") if args.verbose else ""
            # This goes through the each of the data collectors in the case they've been separated by customer journey stage
            for collector in data_collectors:           
                print(f"Time taken for {collector.name} collector: {collector.duration}s") if args.verbose else ""
                duration_times.append(collector.duration)
                for k, v in collector.get_data().items():
                    flattened_collected_data.update({k: v})
                # print(flattened_collected_data)
            
            metrics = calculate_metrics(
                [v for k, v in example.items() if k != "message" and v != ''],
                [v for k, v in flattened_collected_data.items() if k != "message" and v != ''],
                args.verbose,
                )
                
            print(f"Precision: {metrics.precision}\t Recall: {metrics.recall}\t F1: {metrics.f1}") if args.verbose else ""
            print("------------") if args.verbose else ""
            avg_precision += metrics.precision
            avg_recall += metrics.recall
            avg_f1 += metrics.f1
        
        mean_duration = sum(duration_times) / len(duration_times)
        max_duration = round(max(duration_times),2)
        min_duration = round(min(duration_times),2)


        print(
            f"Average collector duration: {mean_duration:.2f}s. Min: {min_duration}s  Max: {max_duration}s"
            ) if not args.verbose else ""    
    
        run_data[i] = {
            "mean_duration_s": round(mean_duration,2),
            "min_duration_s": min_duration,
            "max_duration_s": max_duration,
            "precision": avg_precision / len(test_examples),
            "recall": avg_recall / len(test_examples),
            "f1": avg_f1 / len(test_examples),
        }

    print(run_data)    
    df = pd.DataFrame.from_dict(data=run_data, orient='index')
    df.to_csv(f"src/tests/{args.output_filename}", index=True)
    if loop:
        loop.close()
if __name__ == "__main__":
    main()