import { Stack } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from './context/AuthContext';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <AuthProvider>
          <StatusBar style="light" />
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="index" />
            <Stack.Screen name="auth/login" />
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="recording" />
            <Stack.Screen name="processing" />
            <Stack.Screen name="results" />
            <Stack.Screen name="payment" />
            <Stack.Screen name="debug-auth" />
          </Stack>
        </AuthProvider>
      </GestureHandlerRootView>
    </SafeAreaProvider>
  );
}
