@ui
Feature: Admin UI

    Scenario Outline: Admin page view
        Given user technicaladmin is logged in #FIXME: User var in user
        When user opens link to adminpage
        Then the text Administration is shown
        
#TODO: PAGE view suessful, Text administration is present? #Menu item present 

# TODO: scenarios: dropdown button for admin user and not shown for non-admin users
# TODO: Scenarios: text access denied is present for non-admin users
