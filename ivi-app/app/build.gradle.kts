plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "dev.opencabin.ivi"
    compileSdk = 35
    // AAOS Car API (CarPropertyManager, CarUxRestrictionsManager). 기기에 있는 라이브러리를 쓰므로 APK 에는 들어가지 않는다
    useLibrary("android.car")

    defaultConfig {
        applicationId = "dev.opencabin.ivi"
        minSdk = 31          // 태블릿(Android 12)
        targetSdk = 34       // AAOS 에뮬레이터(API 34)
        versionCode = 5
        versionName = "0.4.1"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    // 영상 화면: 기기에 올린 블랙박스 주행 영상 재생 (tools/push_drive_videos.py)
    implementation("androidx.media3:media3-exoplayer:1.5.1")
    implementation("androidx.media3:media3-ui:1.5.1")

    // 비서 규칙(assistant/)의 JVM 단위 테스트
    testImplementation("junit:junit:4.13.2")
}
