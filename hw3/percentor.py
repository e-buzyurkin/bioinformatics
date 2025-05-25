import subprocess
import re
import argparse
from clearml import Task, Logger
from clearml.automation import PipelineController

pipeline = PipelineController(
    name="Mapping Quality Assessment Pipeline",
    project="Bioinfo",
    version="1.0"
)

def step_one(reads_path: str):
    task = Task.init(project_name="Bioinfo", task_name="FastQC") 
    if ".fastq" not in reads_path:
        subprocess.run(f'fastq-dump {reads_path}', shell=True)
    task.close()

def step_two(reference_path: str):
    task = Task.init(project_name="Bioinfo", task_name="BWA index")
    subprocess.run(f'bwa index {reference_path}', shell=True)
    task.close()

def step_three(reference_path: str, reads_path: str):
    task = Task.init(project_name="Bioinfo", task_name="BWA alignment")
    if ".fastq" not in reads_path:
        reads_path += ".fastq"
    subprocess.run(f'bwa mem {reference_path} {reads_path} > aligned.sam', shell=True)
    task.close()

def step_four():
    task = Task.init(project_name="Bioinfo", task_name="Samtools flagstat")
    result = subprocess.run(['samtools', 'flagstat', 'aligned.sam'], capture_output=True, text=True)
    pattern = r"mapped \((\d+\.\d+)%"
    matching = re.search(pattern, result.stdout)
    if matching:
        percentage = matching.group(1)
        Logger.current_logger().report_text(f'Mapped {percentage}%')
        if float(percentage) > 0.9:
            Logger.current_logger().report_text(f'OK')
            return
        Logger.current_logger().report_text(f'Not OK')
    else:
        Logger.current_logger().report_text('Failed to get percentage')
    task.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Mapping Quality Assessment Pipeline")
    parser.add_argument('--reads_path', type=str, required=True, help="Path to reads file")
    parser.add_argument('--reference_path', type=str, required=True, help="Path to reference file")

    args = parser.parse_args()

    pipeline.add_function_step(
        name="1. FastQC",
        function=step_one,
        function_kwargs={"reads_path": args.reads_path}
    )

    pipeline.add_function_step(
        name="2. BWA Index",
        function=step_two,
        function_kwargs={"reference_path": args.reference_path},
        parents=["1. FastQC"]
    )

    pipeline.add_function_step(
        name="3. BWA Alignment",
        function=step_three,
        function_kwargs={"reference_path": args.reference_path, "reads_path": args.reads_path},
        parents=["2. BWA Index"]
    )

    pipeline.add_function_step(
        name="4. Samtools Flagstat",
        function=step_four,
        parents=["3. BWA Alignment"]
    )

    pipeline.start_locally(run_pipeline_steps_locally=True)