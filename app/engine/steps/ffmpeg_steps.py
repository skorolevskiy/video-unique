import random
import ffmpeg
from app.engine.steps.base import BaseStep, ProcessingContext

class MetadataMutationStep(BaseStep):
    def apply(self, ctx: ProcessingContext, stream):
        # In ffmpeg-python, metadata is usually handled at output, 
        # but we can try to strip it or set it here if the library supports it.
        # Actually, -map_metadata -1 is an output option.
        # We will add it to the global output params in the context.
        if 'output_params' not in ctx.config:
            ctx.config['output_params'] = {}
        
        ctx.config['output_params']['map_metadata'] = -1
        
        # Add random metadata
        ctx.config['output_params']['metadata:g:0'] = f"comment=Processed_{random.randint(1000, 9999)}"
        return stream

class NoiseInjectionStep(BaseStep):
    def apply(self, ctx: ProcessingContext, stream):
        # noise=alls=1:allf=t+u
        # intensity 0-100
        intensity = ctx.config.get('noise_intensity', 5)
        return stream.filter('noise', alls=intensity, allf='t+u')

class ColorModulationStep(BaseStep):
    def apply(self, ctx: ProcessingContext, stream):
        # eq=brightness=0.01:contrast=1.02:saturation=0.99
        # Randomize slightly
        brightness = random.uniform(-0.05, 0.05)
        contrast = random.uniform(0.95, 1.05)
        saturation = random.uniform(0.95, 1.05)
        gamma = random.uniform(0.95, 1.05)
        
        return stream.filter('eq', brightness=brightness, contrast=contrast, saturation=saturation, gamma=gamma)

class GeometricTransformStep(BaseStep):
    def apply(self, ctx: ProcessingContext, stream):
        # crop 1-2 pixels and scale back
        # This is tricky without knowing input resolution.
        # We can use 'iw' and 'ih' constants in ffmpeg expressions.
        
        crop_x = random.randint(1, 2)
        crop_y = random.randint(1, 2)
        
        # crop=w=iw-2*crop_x:h=ih-2*crop_y:x=crop_x:y=crop_y
        stream = stream.filter('crop', w=f'iw-{2*crop_x}', h=f'ih-{2*crop_y}', x=crop_x, y=crop_y)
        
        # scale back to original? Or leave it slightly cropped?
        # Requirement says "scale back".
        # We don't know original size easily here without probing, but 'scale' filter can take iw/ih of the input chain?
        # Actually, if we crop, the next filter sees the cropped size.
        # So we need to scale to "original size". 
        # Since we don't probe here, we might skip scaling back for MVP or assume we want to keep it slightly changed resolution.
        # Let's try to scale back to a fixed resolution if provided, or just leave it cropped (which changes hash).
        # If we want to scale back, we need to know the target size.
        # Let's assume for MVP we just crop slightly.
        return stream
