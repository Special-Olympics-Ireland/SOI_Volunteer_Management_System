# Flutter Development Environment Setup Guide

## Overview

This guide provides step-by-step instructions for setting up the Flutter development environment for the SOI Volunteer Management System. It covers installation, configuration, and project setup for all supported platforms (iOS, Android, and Web).

## Prerequisites

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+ recommended)
- **Hardware**: 8GB+ RAM, SSD storage recommended
- **Git**: Latest version
- **IDE**: VS Code or Android Studio
- **Internet Connection**: Broadband connection for downloads

## 1. Install Flutter SDK

### For macOS

```bash
# 1. Download the Flutter SDK
curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/macos/flutter_macos_3.16.9-stable.zip

# 2. Extract the file
unzip flutter_macos_3.16.9-stable.zip

# 3. Add Flutter to your PATH
export PATH="$PATH:`pwd`/flutter/bin"

# 4. Add to your shell profile for permanent addition
echo 'export PATH="$PATH:$HOME/flutter/bin"' >> ~/.zshrc  # or .bashrc
```

### For Windows

1. Download the Flutter SDK from [flutter.dev](https://flutter.dev/docs/get-started/install/windows)
2. Extract the zip file to a desired location (e.g., `C:\flutter`)
3. Add Flutter to your PATH:
   - Search for "Environment Variables" in Windows search
   - Click "Edit the system environment variables"
   - Click "Environment Variables"
   - Under "System Variables," find and select "Path"
   - Click "Edit"
   - Click "New" and add the path to `flutter\bin` (e.g., `C:\flutter\bin`)
   - Click "OK" to save

### For Linux (Ubuntu)

```bash
# 1. Download the Flutter SDK
wget https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.16.9-stable.tar.xz

# 2. Extract the file
tar xf flutter_linux_3.16.9-stable.tar.xz

# 3. Add Flutter to your PATH
export PATH="$PATH:`pwd`/flutter/bin"

# 4. Add to your shell profile for permanent addition
echo 'export PATH="$PATH:$HOME/flutter/bin"' >> ~/.bashrc
source ~/.bashrc
```

## 2. Verify Installation

Run the following command to verify Flutter is installed correctly:

```bash
flutter doctor
```

This will check your environment and display any issues that need to be addressed.

## 3. Install Platform Dependencies

### Android Development

1. **Install Android Studio**:
   - Download from [developer.android.com](https://developer.android.com/studio)
   - Complete the installation wizard

2. **Configure Android SDK**:
   - Open Android Studio
   - Go to Tools > SDK Manager
   - Select the "SDK Platforms" tab
   - Check "Android 13" (API Level 33) and "Android 7.0" (API Level 24)
   - Select the "SDK Tools" tab
   - Check "Android SDK Build-Tools", "Android SDK Command-line Tools", and "Android Emulator"
   - Click "Apply" to install

3. **Create an Android Virtual Device (AVD)**:
   - Open Android Studio
   - Go to Tools > AVD Manager
   - Click "Create Virtual Device"
   - Select a device (e.g., Pixel 6)
   - Select a system image (e.g., Android 13)
   - Complete the setup

### iOS Development (macOS only)

1. **Install Xcode**:
   - Download from the Mac App Store
   - Open Xcode and accept the license agreement
   - Install additional components if prompted

2. **Configure Xcode command-line tools**:
   ```bash
   sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
   sudo xcodebuild -runFirstLaunch
   ```

3. **Install CocoaPods**:
   ```bash
   sudo gem install cocoapods
   ```

### Web Development

No additional setup is required for web development beyond the Flutter SDK.

## 4. IDE Setup

### VS Code (Recommended)

1. **Install VS Code**:
   - Download from [code.visualstudio.com](https://code.visualstudio.com/)
   - Complete the installation

2. **Install Flutter Extension**:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X or Cmd+Shift+X)
   - Search for "Flutter"
   - Install the Flutter extension by Dart Code

3. **Recommended Additional Extensions**:
   - Dart
   - Flutter Widget Snippets
   - Awesome Flutter Snippets
   - bloc
   - Material Icon Theme
   - Better Comments

### Android Studio

1. **Install Flutter Plugin**:
   - Open Android Studio
   - Go to File > Settings > Plugins
   - Search for "Flutter"
   - Install the Flutter plugin
   - Restart Android Studio when prompted

## 5. Project Setup

### Clone the Repository

```bash
# Create a projects directory if it doesn't exist
mkdir -p ~/projects
cd ~/projects

# Clone the repository
git clone https://github.com/Special-Olympics-Ireland/SOI_Volunteer_Management_System.git
cd SOI_Volunteer_Management_System
```

### Create Flutter Project

```bash
# Create a new Flutter project in the frontend directory
flutter create --org ie.specialolympics --project-name soi_volunteer_app --platforms=android,ios,web frontend

# Navigate to the project directory
cd frontend
```

### Install Dependencies

Edit the `pubspec.yaml` file to add the required dependencies as specified in the Flutter Implementation Guide, then run:

```bash
flutter pub get
```

### Configure Environment Variables

Create a `.env` file for environment-specific configuration:

```bash
# Development environment
touch .env.development
echo "API_URL=https://dev-api.specialolympicsireland.ie" >> .env.development
echo "ENVIRONMENT=development" >> .env.development

# Staging environment
touch .env.staging
echo "API_URL=https://staging-api.specialolympicsireland.ie" >> .env.staging
echo "ENVIRONMENT=staging" >> .env.staging

# Production environment
touch .env.production
echo "API_URL=https://api.specialolympicsireland.ie" >> .env.production
echo "ENVIRONMENT=production" >> .env.production
```

## 6. Project Structure Setup

Create the recommended project structure:

```bash
# Create core directories
mkdir -p lib/config
mkdir -p lib/core/api
mkdir -p lib/core/database
mkdir -p lib/core/services
mkdir -p lib/core/utils
mkdir -p lib/features/auth/data/models
mkdir -p lib/features/auth/data/repositories
mkdir -p lib/features/auth/data/sources
mkdir -p lib/features/auth/domain/entities
mkdir -p lib/features/auth/domain/repositories
mkdir -p lib/features/auth/domain/use_cases
mkdir -p lib/features/auth/presentation/screens
mkdir -p lib/features/auth/presentation/widgets
mkdir -p lib/features/auth/presentation/providers
mkdir -p lib/features/volunteer_profile
mkdir -p lib/features/events
mkdir -p lib/features/tasks
mkdir -p lib/features/notifications
mkdir -p lib/features/settings
mkdir -p lib/shared/widgets
mkdir -p lib/shared/providers
mkdir -p assets/images
mkdir -p assets/fonts
mkdir -p assets/icons
```

## 7. Configure CI/CD

### GitHub Actions Setup

Create a GitHub Actions workflow file:

```bash
mkdir -p .github/workflows
```

Create a file named `.github/workflows/flutter_ci.yml` with the following content:

```yaml
name: Flutter CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.9'
          channel: 'stable'
      - run: cd frontend && flutter pub get
      - run: cd frontend && flutter analyze
      - run: cd frontend && flutter test
      - run: cd frontend && flutter build apk --debug
      - run: cd frontend && flutter build web --release
```

### Codemagic Setup

1. Create a `codemagic.yaml` file in the project root:

```yaml
workflows:
  android-workflow:
    name: Android Build
    max_build_duration: 60
    environment:
      flutter: stable
    scripts:
      - cd frontend
      - flutter packages pub get
      - flutter build apk --release
    artifacts:
      - frontend/build/app/outputs/**/*.apk

  ios-workflow:
    name: iOS Build
    max_build_duration: 60
    environment:
      flutter: stable
      xcode: latest
      cocoapods: default
    scripts:
      - cd frontend
      - flutter packages pub get
      - flutter build ios --release --no-codesign
    artifacts:
      - frontend/build/ios/ipa/*.ipa

  web-workflow:
    name: Web Build
    max_build_duration: 60
    environment:
      flutter: stable
    scripts:
      - cd frontend
      - flutter packages pub get
      - flutter build web --release
    artifacts:
      - frontend/build/web/**
```

## 8. Initial Configuration Files

### Create Theme Configuration

Create a file at `lib/config/theme.dart`:

```dart
import 'package:flutter/material.dart';

class SOIColors {
  // Primary Colors
  static const Color primaryGreen = Color(0xFF2E7D32);
  static const Color primaryBlue = Color(0xFF1976D2);
  
  // Secondary Colors
  static const Color secondaryOrange = Color(0xFFFF6F00);
  static const Color secondaryPurple = Color(0xFF6A1B9A);
  
  // Neutral Colors
  static const Color textPrimary = Color(0xFF212121);
  static const Color textSecondary = Color(0xFF757575);
  static const Color surface = Color(0xFFF5F5F5);
  static const Color background = Color(0xFFFAFAFA);
  
  // Semantic Colors
  static const Color success = Color(0xFF4CAF50);
  static const Color warning = Color(0xFFFF9800);
  static const Color error = Color(0xFFD32F2F);
  static const Color info = Color(0xFF2196F3);
}

class SOITheme {
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: SOIColors.primaryGreen,
        primary: SOIColors.primaryGreen,
        secondary: SOIColors.primaryBlue,
        surface: SOIColors.surface,
        background: SOIColors.background,
        error: SOIColors.error,
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: SOIColors.primaryGreen,
        foregroundColor: Colors.white,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: SOIColors.primaryGreen,
          foregroundColor: Colors.white,
          minimumSize: const Size(double.infinity, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
    );
  }
}
```

### Create Routes Configuration

Create a file at `lib/config/routes.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

// Import screens once they're created
// import 'package:soi_volunteer_app/features/auth/presentation/screens/login_screen.dart';

final GoRouter router = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const Scaffold(
        body: Center(
          child: Text('SOI Volunteer App - Home'),
        ),
      ),
    ),
    // Add more routes as screens are created
  ],
);
```

### Update Main App File

Update the `lib/main.dart` file:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:soi_volunteer_app/config/routes.dart';
import 'package:soi_volunteer_app/config/theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: SOIApp()));
}

class SOIApp extends StatelessWidget {
  const SOIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'SOI Volunteer App',
      theme: SOITheme.lightTheme,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
```

## 9. Testing the Setup

Run the app to verify the setup:

```bash
cd frontend
flutter run
```

This will launch the app on your connected device or emulator.

## 10. Next Steps

After completing the setup:

1. Implement the authentication flow
2. Create the volunteer registration screens
3. Set up API integration with the backend
4. Implement offline data storage

## Troubleshooting

### Common Issues

1. **Flutter doctor shows issues**:
   - Follow the recommendations provided by `flutter doctor`

2. **Android SDK issues**:
   - Ensure ANDROID_HOME environment variable is set
   - Make sure you have accepted all licenses: `flutter doctor --android-licenses`

3. **iOS build fails**:
   - Ensure Xcode is properly installed
   - Run `pod repo update` in the iOS project directory

4. **Package conflicts**:
   - Run `flutter pub cache clean` and then `flutter pub get`

### Getting Help

- **SOI Development Team**: Contact the lead developer for project-specific issues
- **Flutter Documentation**: [flutter.dev/docs](https://flutter.dev/docs)
- **Flutter Community**: [Stack Overflow](https://stackoverflow.com/questions/tagged/flutter)

## Conclusion

You now have a fully configured Flutter development environment for the SOI Volunteer Management System. The project structure follows clean architecture principles and is ready for feature development.

**Next Document**: Refer to `FLUTTER_IMPLEMENTATION_GUIDE.md` for detailed implementation guidelines and code examples. 