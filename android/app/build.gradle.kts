plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "uz.buxoro.hunarmandcontrol"
    compileSdk = 35

    defaultConfig {
        applicationId = "uz.buxoro.hunarmandcontrol"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }
}

kotlin {
    jvmToolchain(17)
}
