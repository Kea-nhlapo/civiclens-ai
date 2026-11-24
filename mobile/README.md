# CivicLens mobile

The Flutter app for CivicLens. Take a photo (or pick one), and the app sends it to the same API the web app uses. You get the photo back with boxes around what was found, the severity, who handles it, and a report you can share straight to WhatsApp or email.

## How it fits together

```
lib/
  main.dart                  starts the app and wakes the server up
  api.dart                   talks to the backend, turns errors into plain messages
  models.dart                the report the API sends back
  theme.dart                 colours, same as the web app
  screens/home_screen.dart   photo, location, note, streetlight toggle
  screens/report_screen.dart the result, with share and copy
  widgets/detection_photo.dart  draws the boxes on the photo
test/                        API client and screen tests
```

The app talks to the API on Cloud Run. The API's limits apply here too, so the app can't run up the bill.

## Running it

You need Flutter and Android Studio (for the Android SDK and an emulator).

The `android/` folder isn't in the repo yet. Generate it once:

```
cd mobile
flutter create . --platforms=android --project-name civiclens --org com.keanhlapo
```

Then add internet access to the release build. Open `android/app/src/main/AndroidManifest.xml` and add this line just above `<application`:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
```

Then:

```
flutter pub get
flutter test
flutter run
```

To build an APK you can install on a phone:

```
flutter build apk --release
```

It ends up in `build/app/outputs/flutter-apk/app-release.apk`.

To point the app at a backend running on your own machine (from the Android emulator):

```
flutter run --dart-define=CIVICLENS_API=http://10.0.2.2:8080
```
