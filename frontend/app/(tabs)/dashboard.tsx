import { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  RefreshControl,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { COLORS, SPACING, FONT_SIZES, BORDER_RADIUS } from '../constants/theme';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function DashboardScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState({
    totalAssessments: 0,
    avgScore: 0,
    bestScore: 0,
  });

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/assessments`);
      const assessments = response.data.assessments || [];

      if (assessments.length > 0) {
        const scores = assessments.map((a: any) =>
          a.analysis.insights?.overall_score || a.analysis.overall_score || 0
        );

        const total = scores.length;
        const sum = scores.reduce((a: number, b: number) => a + b, 0);
        const avg = Math.round(sum / total);
        const best = Math.max(...scores);

        setStats({
          totalAssessments: total,
          avgScore: avg,
          bestScore: best,
        });
      } else {
        setStats({
          totalAssessments: 0,
          avgScore: 0,
          bestScore: 0,
        });
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchStats();
    }, [])
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchStats();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.primary} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Hello, {user?.name?.split(' ')[0] || 'User'}!</Text>
            <Text style={styles.subtitle}>Ready to assess your voice?</Text>
          </View>
        </View>

        {/* Start Assessment Button */}
        <TouchableOpacity
          style={styles.startButton}
          onPress={() => router.push('/recording')}
        >
          <View style={styles.startButtonContent}>
            <View style={styles.startButtonIcon}>
              <Ionicons name="mic" size={32} color={COLORS.textWhite} />
            </View>
            <View style={styles.startButtonText}>
              <Text style={styles.startButtonTitle}>Start New Assessment</Text>
              <Text style={styles.startButtonSubtitle}>Record your voice for analysis</Text>
            </View>
            <Ionicons name="arrow-forward" size={24} color={COLORS.primary} />
          </View>
        </TouchableOpacity>

        {/* Stats Cards */}
        <View style={styles.statsContainer}>
          <Text style={styles.sectionTitle}>Your Stats</Text>
          <View style={styles.statsGrid}>
            <View style={styles.statCard}>
              <Ionicons name="mic-outline" size={32} color={COLORS.primary} />
              <Text style={styles.statValue}>{stats.totalAssessments}</Text>
              <Text style={styles.statLabel}>Assessments</Text>
            </View>
            <View style={styles.statCard}>
              <Ionicons name="trending-up" size={32} color={COLORS.success} />
              <Text style={styles.statValue}>
                {stats.avgScore > 0 ? stats.avgScore : '--'}
              </Text>
              <Text style={styles.statLabel}>Avg Score</Text>
            </View>
            <View style={styles.statCard}>
              <Ionicons name="trophy-outline" size={32} color={COLORS.warning} />
              <Text style={styles.statValue}>
                {stats.bestScore > 0 ? stats.bestScore : '--'}
              </Text>
              <Text style={styles.statLabel}>Best Score</Text>
            </View>
          </View>
        </View>

        {/* Features */}
        <View style={styles.featuresContainer}>
          <Text style={styles.sectionTitle}>Features</Text>
          <View style={styles.featureCard}>
            <Ionicons name="bar-chart" size={24} color={COLORS.primary} />
            <View style={styles.featureContent}>
              <Text style={styles.featureTitle}>Comprehensive Analysis</Text>
              <Text style={styles.featureDescription}>
                Get insights on pitch, pace, tone, clarity and more
              </Text>
            </View>
          </View>
          <View style={styles.featureCard}>
            <Ionicons name="bulb" size={24} color={COLORS.primary} />
            <View style={styles.featureContent}>
              <Text style={styles.featureTitle}>Personalized Training</Text>
              <Text style={styles.featureDescription}>
                Receive custom training questions to improve
              </Text>
            </View>
          </View>
          <View style={styles.featureCard}>
            <Ionicons name="people" size={24} color={COLORS.primary} />
            <View style={styles.featureContent}>
              <Text style={styles.featureTitle}>Voice Archetype</Text>
              <Text style={styles.featureDescription}>
                Discover your unique voice profile
              </Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.backgroundDark,
  },
  scrollContent: {
    paddingBottom: SPACING.xl,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: SPACING.lg,
    paddingTop: SPACING.lg,
    paddingBottom: SPACING.md,
  },
  greeting: {
    fontSize: FONT_SIZES.xxl,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  subtitle: {
    fontSize: FONT_SIZES.md,
    color: COLORS.textLight,
    marginTop: SPACING.xs,
  },
  startButton: {
    backgroundColor: COLORS.background,
    marginHorizontal: SPACING.lg,
    marginVertical: SPACING.md,
    borderRadius: BORDER_RADIUS.lg,
    padding: SPACING.lg,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  startButtonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
  },
  startButtonIcon: {
    width: 60,
    height: 60,
    borderRadius: BORDER_RADIUS.md,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  startButtonText: {
    flex: 1,
  },
  startButtonTitle: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.xs,
  },
  startButtonSubtitle: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
  },
  statsContainer: {
    paddingHorizontal: SPACING.lg,
    marginTop: SPACING.lg,
  },
  sectionTitle: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.md,
  },
  statsGrid: {
    flexDirection: 'row',
    gap: SPACING.md,
  },
  statCard: {
    flex: 1,
    backgroundColor: COLORS.background,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.md,
    alignItems: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  statValue: {
    fontSize: FONT_SIZES.xl,
    fontWeight: 'bold',
    color: COLORS.text,
    marginTop: SPACING.sm,
  },
  statLabel: {
    fontSize: FONT_SIZES.xs,
    color: COLORS.textLight,
    marginTop: SPACING.xs,
  },
  featuresContainer: {
    paddingHorizontal: SPACING.lg,
    marginTop: SPACING.xl,
  },
  featureCard: {
    flexDirection: 'row',
    backgroundColor: COLORS.background,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.md,
    alignItems: 'center',
    gap: SPACING.md,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  featureContent: {
    flex: 1,
  },
  featureTitle: {
    fontSize: FONT_SIZES.md,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: SPACING.xs,
  },
  featureDescription: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
  },
});
