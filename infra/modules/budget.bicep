targetScope = 'subscription'

param budgetName string
param amount int
param contactEmail string
param projectTag string
param budgetStartDate string = utcNow('yyyy-MM-ddT00:00:00Z')

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: budgetName
  properties: {
    amount: amount
    category: 'Cost'
    filter: {
      tags: {
        name: 'project'
        operator: 'In'
        values: [
          projectTag
        ]
      }
    }
    notifications: {
      Actual_GreaterThan_50_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 50
        thresholdType: 'Actual'
        contactEmails: [
          contactEmail
        ]
        contactGroups: []
        contactRoles: []
      }
      Actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: [
          contactEmail
        ]
        contactGroups: []
        contactRoles: []
      }
      Actual_GreaterThan_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: [
          contactEmail
        ]
        contactGroups: []
        contactRoles: []
      }
    }
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStartDate
    }
  }
}

output budgetId string = budget.id
