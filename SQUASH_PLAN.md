# Squash App Improvement Plan

This document outlines the proposed high-impact, low-friction improvements for the colleague squash league application.

## 1. Recent Form Sparklines
- **Description**: Add a row of 5 color-coded indicators (e.g., green for Win, red for Loss) next to player names on the Leaderboard.
- **Utility**: Allows colleagues to see at a glance who is currently "on fire" without clicking into individual profiles.
- **Implementation**: Fetch the last 5 matches for each player in the `list_profiles` route.

## 2. Head-to-Head (H2H) Quick Stats
- **Description**: When viewing another player's profile while logged in, show a dedicated section: "Your Record vs. [Name]".
- **Utility**: Fuels friendly rivalries by highlighting personal history (e.g., "You: 3 wins, Dave: 1 win").
- **Implementation**: Add a H2H lookup query in the `read_profile` route if a `user` is present in the context.

## 3. Smart Match Logging
- **Description**: Streamline the "Log Match" modal to reduce data entry fatigue.
- **Features**:
    - Default "Player 1" to the currently logged-in user.
    - If opened from a Session page, auto-select that session in the dropdown.
- **Utility**: Keeps the barrier to logging matches as low as possible.

## 4. ELO History Graphing
- **Description**: Add a clean line chart to the Profile page showing ELO change over time.
- **Utility**: Visualizes progress and makes the "ELO grind" more psychologically rewarding.
- **Implementation**: Utilize the existing `EloHistory` collection and a lightweight charting library like `Chart.js`.
