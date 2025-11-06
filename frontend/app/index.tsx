import { useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from './context/AuthContext';
import { COLORS, FONT_SIZES, SPACING } from './constants/theme';

export default function SplashScreen() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      setTimeout(() => {
        if (user) {
          router.replace('/(tabs)/dashboard');
        } else {
          router.replace('/auth/login');
        }
      }, 1500);
    }
  }, [user, loading]);

  return (
    <View style={styles.container}>
      <Text style={styles.logo}>🎤</Text>
      <Text style={styles.title}>The Mirror Note</Text>
      <Text style={styles.subtitle}>AI Voice Assessment Platform</Text>
      <ActivityIndicator 
        size="large" 
        color={COLORS.primary} 
        style={styles.loader} 
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: SPACING.xl,
  },
  logo: {
    fontSize: 80,
    marginBottom: SPACING.lg,
  },
  title: {
    fontSize: FONT_SIZES.xxxl,
    fontWeight: 'bold',
    color: COLORS.textWhite,
    marginBottom: SPACING.sm,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: FONT_SIZES.md,
    color: COLORS.textWhite,
    opacity: 0.9,
    textAlign: 'center',
    marginBottom: SPACING.xl,
  },
  loader: {
    marginTop: SPACING.xxl,
  },
});
