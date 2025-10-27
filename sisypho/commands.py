#!/usr/bin/env python3
"""
Command implementations for Sisypho SDK CLI.

This module contains the actual command implementations for create and run.
"""

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import RecorderContext, await_task_completion, Workflow


async def create_command(args: argparse.Namespace) -> None:
    """Create a new workflow (optionally with recording)."""
    print("🎬 Sisypho Workflow Creator")
    print("=" * 40)
    
    task_prompt = args.task
    print(f"📝 Task: {task_prompt}")
    
    recording = None
    
    # Only record if --record flag is present
    if args.record:
        print("🎥 Starting recording... Press Enter when done recording actions.")
        
        try:
            with RecorderContext() as recorder:
                # Wait for user to complete actions
                await_task_completion()
            
            recording = recorder.get_recording()
            
            if recording:
                print(f"✅ Recorded {len(recording)} actions")
            else:
                print("⚠️  No actions were recorded, but continuing without recording.")
        except KeyboardInterrupt:
            print("\n⏹️  Recording stopped by user")
            return
        except Exception as e:
            print(f"⚠️  Recording failed: {e}, but continuing without recording.")
    else:
        print("ℹ️  No recording requested (use --record to record actions)")
    
    try:
        # Create workflow (with or without recording)
        workflow = Workflow(recording or "", task_prompt)
        await workflow.generate_code()
        
        # Save workflow
        if args.output:
            output_path = Path(args.output)
        else:
            # Auto-generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_task = "".join(c for c in task_prompt[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_task = safe_task.replace(' ', '_')
            output_path = Path(f"workflow_{safe_task}_{timestamp}.json")
        
        workflow.save(str(output_path))
        print(f"💾 Workflow saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error creating workflow: {e}")


async def run_command(args: argparse.Namespace) -> None:
    """Run an existing workflow or execute the default test workflow."""
    print("🚀 Sisypho Workflow Runner")
    print("=" * 40)
    
    # Determine which workflow to run
    if args.workflow:
        workflow_path = Path(args.workflow)
        if not workflow_path.exists():
            print(f"❌ Workflow file not found: {workflow_path}")
            return
        print(f"📁 Loading workflow from: {workflow_path}")
        
        # Load existing workflow
        try:
            with open(workflow_path, 'r') as f:
                workflow_data = json.load(f)
            
            # Create workflow object from loaded data
            workflow = Workflow.from_dict(workflow_data)
            print(f"📝 Task: {workflow.task_prompt}")
            
        except Exception as e:
            print(f"❌ Error loading workflow: {e}")
            return
            
    elif args.interactive:
        # Run the default test workflow (from test.py)
        print("🎯 Running default test workflow...")
        task_prompt = "open chrome, open a new tab, and type 'Hello World'"
        
        with RecorderContext() as recorder:
            await_task_completion()
        
        recording = recorder.get_recording()
        workflow = Workflow(recording, task_prompt)
        await workflow.generate_code()
        
    else:
        print("Error: Either --workflow or --interactive is required for run command")
        return
    
    # Override task if provided
    if args.task:
        workflow.task_prompt = args.task
        print(f"📝 Override task: {workflow.task_prompt}")
    
    try:
        print("🏃 Executing workflow...")
        result = workflow.run_workflow()
        
        if result:
            print("✅ Workflow executed successfully!")
        else:
            print("⚠️  Workflow execution completed with warnings")
            
        # Save the workflow
        workflow.save()
        print("💾 Workflow saved")
        
    except Exception as e:
        print(f"❌ Error running workflow: {e}")


# For backward compatibility, also provide the original test functionality
async def run_test_workflow() -> None:
    """Run the original test workflow functionality."""
    print("🧪 Running Sisypho Test Workflow")
    print("=" * 40)
    
    task_prompt = "open chrome, open a new tab, and type 'Hello World'"
    print(f"📝 Task: {task_prompt}")

    with RecorderContext() as recorder:
        # do some actions that should be recorded
        await await_task_completion()

    recording = recorder.get_recording()

    workflow = Workflow(recording, task_prompt)
    await workflow.generate_code()
    result = workflow.run_workflow()

    workflow.save()
    print("✅ Test workflow completed and saved")
