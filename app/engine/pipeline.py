import os
import ffmpeg
from typing import List
from app.engine.steps.base import BaseStep, ProcessingContext

class Pipeline:
    def __init__(self, steps: List[BaseStep]):
        self.steps = steps

    def run(self, ctx: ProcessingContext) -> str:
        """
        Runs the pipeline and returns the path to the output file.
        """
        # Start with the input file
        stream = ffmpeg.input(ctx.input_path)
        
        # Apply all steps
        for step in self.steps:
            stream = step.apply(ctx, stream)
            
        # Define output path
        output_filename = f"processed_{os.path.basename(ctx.input_path)}"
        output_path = os.path.join(ctx.temp_dir, output_filename)
        
        # Get output parameters from config or defaults
        output_params = ctx.config.get('output_params', {})
        
        # Run ffmpeg
        # overwrite_output=True is -y
        runner = stream.output(output_path, **output_params)
        
        print(f"Running FFmpeg command: {' '.join(ffmpeg.compile(runner))}")
        runner.run(overwrite_output=True)
        
        return output_path
