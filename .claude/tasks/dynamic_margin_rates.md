# Dynamic Margin Rate Implementation Plan

## Overview
Implement dynamic margin rate handling for IG Markets to account for different margin rates based on trading hours (market hours vs overnight/weekend rates).

## Problem Statement
- IG Markets applies different margin rates based on time:
  - Standard rates during market hours
  - Higher rates for overnight positions
  - Different rates for weekend positions
- Current system likely uses static margin rates
- Need to dynamically adjust position sizing and risk calculations based on current margin rates

## Research Requirements
1. **IG Markets Margin Structure**
   - Document standard vs overnight margin rates for different asset classes
   - Identify market hours for different instruments (indices, forex, commodities)
   - Understand rate transition timing (when do rates change)
   - Research IG API endpoints for margin rate information

2. **Current System Analysis**
   - Locate existing margin calculation logic
   - Identify where position sizing occurs
   - Review risk management calculations
   - Check if any time-based logic already exists

## Implementation Plan

### Phase 1: Research and Analysis
- [ ] Research IG Markets margin rate documentation
- [ ] Analyze current codebase for margin-related calculations
- [ ] Map out current data flow for position sizing

### Phase 2: Design Dynamic Margin System
- [ ] Design margin rate data structure
- [ ] Plan scheduler for rate updates
- [ ] Design API integration for real-time rates (if available)
- [ ] Plan fallback logic for rate determination

### Phase 3: Implementation
- [ ] Create margin rate configuration system
- [ ] Implement time-based margin rate scheduler
- [ ] Update position sizing calculations
- [ ] Modify risk management logic
- [ ] Add logging for margin rate changes

### Phase 4: Testing and Validation
- [ ] Test with different time scenarios
- [ ] Validate calculations match IG's actual margins
- [ ] Test edge cases (market transitions, weekends)
- [ ] Performance testing for real-time updates

## Key Components to Implement

1. **Margin Rate Manager**
   - Track current rates for all instruments
   - Handle rate transitions
   - Provide current rate lookup

2. **Time Zone Handler**
   - Handle different market time zones
   - Determine current trading session
   - Calculate rate transition times

3. **Position Calculator Updates**
   - Use dynamic margins for position sizing
   - Adjust risk calculations in real-time
   - Handle margin calls due to rate changes

4. **Configuration System**
   - Store margin rate schedules
   - Handle different rates per instrument type
   - Allow manual rate overrides

## Success Criteria
- Position sizes automatically adjust based on current margin rates
- System correctly identifies market hours vs overnight periods
- Risk management accounts for margin rate changes
- Comprehensive logging of margin rate transitions
- Backward compatibility with existing trading logic

## Risks and Mitigation
- **Risk**: Incorrect margin rates leading to position sizing errors
  - **Mitigation**: Thorough testing and validation against IG's actual rates
- **Risk**: Rate transition timing issues
  - **Mitigation**: Buffer periods and conservative defaults
- **Risk**: API availability for real-time rates
  - **Mitigation**: Fallback to configured schedules

## Next Steps
1. Start with research on IG Markets margin structure
2. Analyze current codebase implementation
3. Get approval for implementation approach
4. Begin phased implementation