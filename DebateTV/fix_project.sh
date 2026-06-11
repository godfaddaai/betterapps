#!/bin/bash

echo "🔧 Fixing DebateTV Xcode Project..."

# Navigate to project directory
cd DebateTVAIDebateArena

# List all Swift files to confirm they exist
echo "📁 Swift files found:"
find . -name "*.swift" -type f | head -20

echo ""
echo "✅ Files exist! Now:"
echo "1. Open DebateTVAIDebateArena.xcodeproj in Xcode"
echo "2. In the navigator, right-click 'DebateTVAIDebateArena' folder"
echo "3. Choose 'Add Files to DebateTVAIDebateArena...'"
echo "4. Select all .swift files from Views/, Models/, Services/, Theme/, Components/"
echo "5. Click Add (don't copy items)"
echo "6. Build with ⌘B"
echo ""
echo "Alternative: Create new Xcode project and copy the Swift files into it"