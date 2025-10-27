import asyncio
from sisypho.utils import RecorderContext, await_task_completion, Workflow

# def byo_cua(prompt: str) -> str:
#     # TODO: implement your own cua/cua library call here.
#     return "some result from executing byo_cua with prompt " + prompt

async def main():
    task_prompt = "open chrome, open a new tab, and type 'Hello World'"

    with RecorderContext() as recorder:
        # do some actions that should be recorded
        await_task_completion()
        # OR
        # byo_cua(task_prompt)

    recording = recorder.get_recording()

    workflow = Workflow(recording, task_prompt)
    await workflow.generate_code()
    result = workflow.run_workflow()

    workflow.save()

if __name__ == "__main__":
    asyncio.run(main())