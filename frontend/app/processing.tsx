import { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import * as FileSystem from 'expo-file-system/legacy';
import { useAuth } from './context/AuthContext';
import { COLORS, SPACING, FONT_SIZES, BORDER_RADIUS } from './constants/theme';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function ProcessingScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const params = useLocalSearchParams();
  const [stage, setStage] = useState('uploading');
  const [progress, setProgress] = useState(0);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    processAudio();
  }, []);

  const processAudio = async () => {
    try {
      const audioUri = params.audioUri as string;
      const mode = params.mode as string;
      const recordingTime = parseInt(params.recordingTime as string);

      // Stage 1: Upload
      setStage('uploading');
      setProgress(25);

      // Verify the recording file exists before reading
      const fileInfo = await FileSystem.getInfoAsync(audioUri);
      if (!fileInfo.exists) {
        throw new Error('Recording file not found. Please re-record and try again.');
      }

      // Read audio file as base64
      const audioBase64 = await FileSystem.readAsStringAsync(audioUri, {
        // Use string literal for SDK compatibility
        encoding: 'base64',
      });

      // Stage 2: Transcribe
      setStage('transcribing');
      setProgress(50);

      // Send to backend
      const response = await axios.post(`${BACKEND_URL}/api/analyze-voice`, {
        audio_base64: audioBase64,
        user_id: user?.id || 'demo_user',
        recording_mode: mode,
        recording_time: recordingTime,
      });

      setAssessmentId(response.data.assessment_id);

      // Stage 3: Analyze
      setStage('analyzing');
      setProgress(75);

      // Wait a bit for dramatic effect
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Stage 4: Complete
      setStage('generating');
      setProgress(100);

      await new Promise(resolve => setTimeout(resolve, 500));

      // Navigate to results
      router.replace({
        pathname: '/results',
        params: { assessmentId: response.data.assessment_id },
      });
    } catch (err: any) {
      console.error('Processing error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to process audio');
    }
  };

  const stages = [
    { id: 'uploading', label: 'Uploading Audio', icon: 'cloud-upload' },
    { id: 'transcribing', label: 'Transcribing Speech', icon: 'text' },
    { id: 'analyzing', label: 'Analyzing Voice', icon: 'analytics' },
    { id: 'generating', label: 'Generating Report', icon: 'document-text' },
  ];

  const getCurrentStageIndex = () => {
    return stages.findIndex(s => s.id === stage);
  };

  if (error) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle" size={80} color={COLORS.error} />
          <Text style={styles.errorTitle}>Processing Failed</Text>
          <Text style={styles.errorMessage}>{error}</Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => router.back()}
          >
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Processing Your Voice</Text>
        <Text style={styles.subtitle}>
          This may take a few moments. Please don't close the app.
        </Text>

        {/* Progress Indicator */}
        <View style={styles.progressContainer}>
          <View style={styles.progressCircle}>
            <ActivityIndicator size="large" color={COLORS.primary} />
            <Text style={styles.progressText}>{progress}%</Text>
          </View>
        </View>

        {/* Stage Indicators */}
        <View style={styles.stagesContainer}>
          {stages.map((stageItem, index) => {
            const isActive = index === getCurrentStageIndex();
            const isCompleted = index < getCurrentStageIndex();

            return (
              <View key={stageItem.id} style={styles.stageItem}>
                <View
                  style={[
                    styles.stageIcon,
                    isActive && styles.stageIconActive,
                    isCompleted && styles.stageIconCompleted,
                  ]}
                >
                  <Ionicons
                    name={isCompleted ? 'checkmark' : (stageItem.icon as any)}
                    size={24}
                    color={
                      isActive || isCompleted
                        ? COLORS.textWhite
                        : COLORS.textLight
                    }
                  />
                </View>
                <View style={styles.stageInfo}>
                  <Text
                    style={[
                      styles.stageLabel,
                      isActive && styles.stageLabelActive,
                    ]}
                  >
                    {stageItem.label}
                  </Text>
                  {isActive && (
                    <Text style={styles.stageStatus}>In progress...</Text>
                  )}
                  {isCompleted && (
                    <Text style={styles.stageStatusCompleted}>Complete</Text>
                  )}
                </View>
              </View>
            );
          })}
        </View>

        {/* Fun Facts */}
        <View style={styles.tipCard}>
          <Ionicons name="bulb" size={24} color={COLORS.primary} />
          <Text style={styles.tipText}>
            Did you know? The average person speaks at 125-150 words per minute in conversation.
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.backgroundDark,
  },
  content: {
    flex: 1,
    paddingHorizontal: SPACING.lg,
    paddingTop: SPACING.xxl,
  },
  title: {
    fontSize: FONT_SIZES.xxl,
    fontWeight: 'bold',
    color: COLORS.text,
    textAlign: 'center',
    marginBottom: SPACING.sm,
  },
  subtitle: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
    textAlign: 'center',
    marginBottom: SPACING.xl,
  },
  progressContainer: {
    alignItems: 'center',
    marginVertical: SPACING.xl,
  },
  progressCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: COLORS.background,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 8,
  },
  progressText: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
    marginTop: SPACING.sm,
  },
  stagesContainer: {
    marginTop: SPACING.xl,
    gap: SPACING.lg,
  },
  stageItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
  },
  stageIcon: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stageIconActive: {
    backgroundColor: COLORS.primary,
  },
  stageIconCompleted: {
    backgroundColor: COLORS.success,
  },
  stageInfo: {
    flex: 1,
  },
  stageLabel: {
    fontSize: FONT_SIZES.md,
    color: COLORS.textLight,
    fontWeight: '500',
  },
  stageLabelActive: {
    color: COLORS.text,
    fontWeight: 'bold',
  },
  stageStatus: {
    fontSize: FONT_SIZES.xs,
    color: COLORS.primary,
    marginTop: SPACING.xs,
  },
  stageStatusCompleted: {
    fontSize: FONT_SIZES.xs,
    color: COLORS.success,
    marginTop: SPACING.xs,
  },
  tipCard: {
    flexDirection: 'row',
    backgroundColor: COLORS.background,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.md,
    marginTop: SPACING.xl,
    gap: SPACING.md,
    alignItems: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  tipText: {
    flex: 1,
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
    lineHeight: 20,
  },
  errorContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: SPACING.xl,
  },
  errorTitle: {
    fontSize: FONT_SIZES.xl,
    fontWeight: 'bold',
    color: COLORS.text,
    marginTop: SPACING.lg,
    marginBottom: SPACING.sm,
  },
  errorMessage: {
    fontSize: FONT_SIZES.md,
    color: COLORS.textLight,
    textAlign: 'center',
    marginBottom: SPACING.xl,
  },
  retryButton: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: SPACING.xl,
    paddingVertical: SPACING.md,
    borderRadius: BORDER_RADIUS.md,
  },
  retryButtonText: {
    color: COLORS.textWhite,
    fontSize: FONT_SIZES.md,
    fontWeight: 'bold',
  },
});
