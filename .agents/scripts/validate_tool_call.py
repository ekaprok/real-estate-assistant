import sys
import json
import re

def main():
    try:
        # Read the payload from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            # If no input is provided, default to allow
            print(json.dumps({"decision": "allow"}), flush=True)
            return

        payload = json.loads(input_data)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        # We intercept 'run_command' calls
        if tool_name == "run_command":
            command_line = args.get("CommandLine", "")

            # Regex pattern to match destructive command patterns like:
            # - rm -rf /
            # - rm -r -f /
            # - rm -fr /something
            # We match 'rm' followed by spaces, flags containing 'r' and 'f', and targeting '/' or directories directly under root.
            destructive_regexes = [
                r"\brm\s+-[a-zA-Z0-9]*[rf][a-zA-Z0-9]*\s+/",
                r"\brm\s+-[a-zA-Z0-9]*r[a-zA-Z0-9]*\s+-[a-zA-Z0-9]*f[a-zA-Z0-9]*\s+/",
                r"\brm\s+-[a-zA-Z0-9]*f[a-zA-Z0-9]*\s+-[a-zA-Z0-9]*r[a-zA-Z0-9]*\s+/",
            ]

            is_destructive = False
            for pattern in destructive_regexes:
                if re.search(pattern, command_line):
                    is_destructive = True
                    break

            # Fallback direct string match for clean normalized space representations
            normalized_cmd = " ".join(command_line.split())
            if "rm -rf /" in normalized_cmd or "rm -fr /" in normalized_cmd:
                is_destructive = True

            if is_destructive:
                response = {
                    "decision": "deny",
                    "reason": f"Execution blocked: The command '{command_line}' is destructive and not allowed."
                }
                print(json.dumps(response), flush=True)
                return

        # Safe command or other tools are allowed
        print(json.dumps({"decision": "allow"}), flush=True)

    except Exception as e:
        # Log error to stderr for visibility and default to allow to prevent lockouts
        print(f"Error in validate_tool_call.py: {e}", file=sys.stderr, flush=True)
        print(json.dumps({"decision": "allow"}), flush=True)

if __name__ == "__main__":
    main()
