using '../main.bicep'

param location = 'eastus'
param resourceGroupName = 'rg-ai103-free-lab'
param nameSuffix = 'dev001'
param owner = 'local-learner'
param expiresAt = '2026-08-31'
param budgetAmount = 10
param budgetContactEmail = ''

param deployFoundry = false
param deploySearch = false
param deployStorage = false
param deployContentUnderstanding = false
