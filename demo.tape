# ==============================================================================
# VHS configuration for Real Estate Assistant YouTube Demo
# Target dimensions: 720p HD (1280x720) for standard 16:9 aspect ratio.
#
# Long reports are piped through `less -R` so each result starts at the TOP of
# the screen (instead of scrolling past it) and we page down so viewers can
# read the report from the beginning. `-R` preserves ANSI colors.
# ==============================================================================

Output demo.mp4

Set Width 1280
Set Height 720
Set FontSize 14

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
# Pipe into `less -R` so the report opens at the top; -F would auto-exit on a
# short report, so we keep the pager open and scroll manually.
Type "agents-cli run 'Union City, NJ' | less -R"
Sleep 500ms
Enter
# Give the run time to complete and populate the pager.
Sleep 5s
# Read the top of the report, page down, then quit the pager.
Sleep 1s
Down@200ms 8
Sleep 1s
Type "q"

Type "clear"
Enter
Sleep 1s

# ------------------------------------------------------------------------------
# Scenario 2: Restricted Municipality (New York City, NY)
# ------------------------------------------------------------------------------
Type "# 2. Checking a restricted municipality..."
Enter
Sleep 1s
Type "agents-cli run 'New York City, NY' | less -R"
Sleep 500ms
Enter
Sleep 6s
Sleep 1s
Down@200ms 10
Sleep 1s
Type "q"

Type "clear"
Enter
Sleep 1s

# ------------------------------------------------------------------------------
# Scenario 3: Allowed Municipality (Lincoln, NH) - full legal + financial report
# ------------------------------------------------------------------------------
Type "# 3. Checking an allowed municipality (full analysis)..."
Enter
Sleep 1s
Type "agents-cli run 'Lincoln, NH' | less -R"
Sleep 500ms
Enter
Sleep 8s
Sleep 1s
# Scroll further so the financial section at the bottom of the report is shown.
Down@150ms 50
Sleep 2s
Type "q"

Type "clear"
Enter
Sleep 1s

# ------------------------------------------------------------------------------
# Scenario 4: Invalid Query, e.g. not relevant to STRs (Ignored)
# ------------------------------------------------------------------------------
Type "# 4. Inputting an invalid query (not relevant to STRs)..."
Enter
Sleep 1s
# Short output for this one, so a pager is unnecessary; show it inline.
Type "agents-cli run 'What is the history of Austin?'"
Sleep 500ms
Enter
Sleep 5s

Type "clear"
Enter
Sleep 1s

# ------------------------------------------------------------------------------
# Scenario 5: Typo Handling ("Astn TX")
# ------------------------------------------------------------------------------
Type "# 5. Handling typos (resolves 'Astn' -> 'Austin, TX')..."
Enter
Sleep 1s
Type "agents-cli run 'Astn' | less -R"
Sleep 500ms
Enter
Sleep 8s
Sleep 1s
Down@200ms 12
Sleep 1s
Type "q"

# Finished
Type "# Demo complete!"
Enter
Sleep 2s
