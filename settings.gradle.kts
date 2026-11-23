/* Legt die gemeinsamen Plugin- und Paketquellen für den Android-Build fest. */
pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }
rootProject.name = "LokZeitleiste"
include(":app")
