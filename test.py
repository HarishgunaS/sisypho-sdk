from sisypho.utils import RecorderContext, await_task_completion, Workflow

def byo_cua(prompt: str) -> str:
    # TODO: implement your own cua/cua library call here.
    return "some result from executing byo_cua with prompt " + prompt

task_prompt = "open chrome, open a new tab, and type 'Hello World'"

with RecorderContext() as recorder:
    # do some actions that should be recorded
    await_task_completion()
    # OR
    # byo_cua(task_prompt)

recording = recorder.get_recording()


api_key = "some-api-key"
workflow = Workflow(api_key, recording, task_prompt)
workflow.generate_code()
result = workflow.run_workflow(fallback_cua=byo_cua)

workflow.save()