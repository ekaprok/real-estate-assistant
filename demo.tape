# ==============================================================================
# VHS configuration for Real Estate Assistant YouTube Demo
# Target dimensions: 720p HD (1280x720) for standard 16:9 aspect ratio.
# ==============================================================================

Output demo.mp4

# Set FontSize 16

# Initial terminal setup
Type "clear"
Enter
Sleep 1s

# ------------------------------------------------------------------------------
# Scenario 1: Banned Municipality (Union City, NJ)
# ------------------------------------------------------------------------------
Type "# 1. Checking a banned municipality (fast macro screen)..."
Enter
Sleep 1s
Type "agents-cli run 'Union City, NJ'"
Sleep 500ms
Enter
# Banned municipalities short-circuit after the macro legal screen
Sleep 5s

Type "clear"
Enter
Sleep 1s

# ------------------------------------------------------------------------------
# Scenario 2: Restricted Municipality (New York City, NY)
# ------------------------------------------------------------------------------
Type "# 2. Checking a restricted municipality..."
Enter
Sleep 1s
Type "agents-cli run 'New York City, NY'"
Sleep 500ms
Enter
Sleep 5s

Type "clear"
Enter
Sleep 1s

# ------------------------------------------------------------------------------
# Scenario 3: Invalid Query, e.g. not relevant to STRs (Ignored)
# ------------------------------------------------------------------------------
Type "# 3. Inputting an invalid query..."
Enter
Sleep 1s
Type "agents-cli run 'Where is Austin?'"
Sleep 500ms
Enter
Sleep 5s

Type "clear"
Enter
Sleep 1s

# ------------------------------------------------------------------------------
# Scenario 4: Typo Handling ("Astn TX")
# ------------------------------------------------------------------------------
Type "# 4. Handling typos (resolves 'Astn' -> 'Austin, TX')..."
Enter
Sleep 1s
Type "agents-cli run 'Astn'"
Sleep 500ms
Enter
Sleep 5s

# Finished
Type "# Demo complete!"
Enter
Sleep 2s
