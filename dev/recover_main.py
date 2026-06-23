import json

transcript_path = "/Users/dangvo/.gemini/antigravity-ide/brain/f96f56be-499a-4027-885c-f5eb81333715/.system_generated/logs/transcript.jsonl"
edits = []

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            step = json.loads(line)
        except:
            continue
        if 'tool_calls' in step and step['tool_calls']:
            for call in step['tool_calls']:
                name = call.get('function_name', call.get('name', ''))
                args = call.get('arguments', {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except:
                        pass
                if isinstance(args, dict):
                    target = args.get('TargetFile', '')
                    if 'main.py' in target:
                        edits.append(args)

with open('recovered_edits.txt', 'w') as f:
    for i, edit in enumerate(edits):
        f.write(f"--- Edit {i} ---\n")
        if 'ReplacementContent' in edit:
            f.write("StartLine: " + str(edit.get('StartLine')) + "\n")
            f.write("TargetContent:\n" + str(edit.get('TargetContent')) + "\n")
            f.write("ReplacementContent:\n" + str(edit.get('ReplacementContent')) + "\n")
        elif 'ReplacementChunks' in edit:
            for chunk in edit['ReplacementChunks']:
                f.write("StartLine: " + str(chunk.get('StartLine')) + "\n")
                f.write("TargetContent:\n" + str(chunk.get('TargetContent')) + "\n")
                f.write("ReplacementContent:\n" + str(chunk.get('ReplacementContent')) + "\n")

