import { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ScrollView,
  Dimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';
import { COLORS, SPACING, FONT_SIZES, BORDER_RADIUS } from './constants/theme';

const { width } = Dimensions.get('window');
const MAX_RECORDING_DURATION = 120000; // 2 minutes in milliseconds

// Sample texts for guided mode
const SAMPLE_TEXTS = [
  {
    id: 1,
    title: 'Introduction',
    category: 'Professional',
    content: 'Hello, my name is Alex Johnson. I have over five years of experience in software development and project management. I specialize in building scalable web applications and leading cross-functional teams. I am passionate about using technology to solve real-world problems and deliver value to users.',
  },
  {
    id: 2,
    title: 'Product Pitch',
    category: 'Business',
    content: 'Our innovative platform revolutionizes how businesses manage their customer relationships. With AI-powered insights and seamless integration capabilities, we help companies increase customer satisfaction by up to forty percent while reducing operational costs. Join over five thousand companies already transforming their customer experience.',
  },
  {
    id: 3,
    title: 'Storytelling',
    category: 'Creative',
    content: 'The sun was setting over the mountains, casting long shadows across the valley. Sarah stood at the edge of the cliff, her heart pounding with anticipation. This was the moment she had been waiting for, the culmination of months of preparation. With a deep breath, she took her first step forward into the unknown.',
  },
];

export default function RecordingScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<'free' | 'guided' | null>(null);
  const [selectedText, setSelectedText] = useState(SAMPLE_TEXTS[0]);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioUri, setAudioUri] = useState<string | null>(null);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    requestPermissions();
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const requestPermissions = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      setPermissionGranted(status === 'granted');
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Microphone permission is required to record audio.');
      }
      
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
    } catch (error) {
      console.error('Error requesting permissions:', error);
    }
  };

  const startRecording = async () => {
    if (!permissionGranted) {
      Alert.alert('Permission Required', 'Please grant microphone permission to record.');
      await requestPermissions();
      return;
    }

    try {
      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      setRecording(newRecording);
      setIsRecording(true);
      setRecordingTime(0);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => {
          const newTime = prev + 1;
          // Auto-stop at 2 minutes
          if (newTime >= 120) {
            stopRecording();
          }
          return newTime;
        });
      }, 1000);
    } catch (error) {
      console.error('Failed to start recording', error);
      Alert.alert('Error', 'Failed to start recording. Please try again.');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;

    try {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      // Persist the recording to a stable cache path so it survives reloads
      if (uri) {
        const recordingsDir = FileSystem.cacheDirectory + 'recordings';
        const dirInfo = await FileSystem.getInfoAsync(recordingsDir);
        if (!dirInfo.exists) {
          await FileSystem.makeDirectoryAsync(recordingsDir, { intermediates: true });
        }

        const fileName = `recording-${Date.now()}.m4a`;
        const targetPath = `${recordingsDir}/${fileName}`;
        await FileSystem.copyAsync({ from: uri, to: targetPath });
        setAudioUri(targetPath);
      } else {
        setAudioUri(null);
      }
      setRecording(null);
    } catch (error) {
      console.error('Failed to stop recording', error);
      Alert.alert('Error', 'Failed to stop recording. Please try again.');
    }
  };

  const playRecording = async () => {
    if (!audioUri) return;

    try {
      const { sound } = await Audio.Sound.createAsync({ uri: audioUri });
      await sound.playAsync();
    } catch (error) {
      console.error('Failed to play recording', error);
      Alert.alert('Error', 'Failed to play recording.');
    }
  };

  const submitRecording = () => {
    if (!audioUri) {
      Alert.alert('No Recording', 'Please record your voice first.');
      return;
    }

    // Navigate to processing screen with audio data
    router.push({
      pathname: '/processing',
      params: {
        audioUri,
        mode,
        recordingTime,
      },
    });
  };

  const resetRecording = () => {
    setAudioUri(null);
    setRecordingTime(0);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Mode selection screen
  if (!mode) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color={COLORS.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Choose Recording Mode</Text>
        </View>

        <ScrollView contentContainerStyle={styles.modeSelection}>
          <TouchableOpacity
            style={styles.modeCard}
            onPress={() => setMode('free')}
          >
            <View style={styles.modeIcon}>
              <Ionicons name="mic" size={40} color={COLORS.primary} />
            </View>
            <Text style={styles.modeTitle}>Free Speaking</Text>
            <Text style={styles.modeDescription}>
              Speak freely about any topic. Perfect for natural conversation assessment.
            </Text>
            <View style={styles.modeBadge}>
              <Ionicons name="flash" size={16} color={COLORS.primary} />
              <Text style={styles.modeBadgeText}>Quick & Easy</Text>
            </View>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.modeCard}
            onPress={() => setMode('guided')}
          >
            <View style={styles.modeIcon}>
              <Ionicons name="document-text" size={40} color={COLORS.primary} />
            </View>
            <Text style={styles.modeTitle}>Guided Speaking</Text>
            <Text style={styles.modeDescription}>
              Read from a provided sample text. Best for consistent analysis and comparison.
            </Text>
            <View style={styles.modeBadge}>
              <Ionicons name="school" size={16} color={COLORS.warning} />
              <Text style={[styles.modeBadgeText, { color: COLORS.warning }]}>
                Structured
              </Text>
            </View>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setMode(null)} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={COLORS.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>
          {mode === 'free' ? 'Free Speaking' : 'Guided Speaking'}
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.recordingContent}>
        {mode === 'guided' && (
          <View style={styles.textCard}>
            <Text style={styles.textCategory}>{selectedText.category}</Text>
            <Text style={styles.textTitle}>{selectedText.title}</Text>
            <ScrollView style={styles.textScrollView}>
              <Text style={styles.textContent}>{selectedText.content}</Text>
            </ScrollView>
            <TouchableOpacity style={styles.changeTextButton}>
              <Text style={styles.changeTextButtonText}>Change Text</Text>
            </TouchableOpacity>
          </View>
        )}

        {mode === 'free' && (
          <View style={styles.instructionCard}>
            <Ionicons name="information-circle" size={32} color={COLORS.primary} />
            <Text style={styles.instructionTitle}>Tips for Best Results</Text>
            <Text style={styles.instructionText}>
              • Speak naturally and clearly{'\n'}
              • Find a quiet environment{'\n'}
              • Record for at least 30 seconds{'\n'}
              • Maximum duration: 2 minutes
            </Text>
          </View>
        )}

        {/* Recording Visualizer */}
        <View style={styles.visualizerCard}>
          <View style={styles.timeDisplay}>
            <Text style={styles.timeText}>{formatTime(recordingTime)}</Text>
            <Text style={styles.timeLimit}>/ 2:00</Text>
          </View>

          {/* Animated Waveform (simplified) */}
          <View style={styles.waveformContainer}>
            {isRecording ? (
              <View style={styles.waveformActive}>
                {[...Array(20)].map((_, i) => (
                  <View
                    key={i}
                    style={[
                      styles.waveBar,
                      {
                        height: Math.random() * 60 + 20,
                        backgroundColor: COLORS.primary,
                      },
                    ]}
                  />
                ))}
              </View>
            ) : (
              <Ionicons
                name={audioUri ? 'checkmark-circle' : 'mic-outline'}
                size={80}
                color={audioUri ? COLORS.success : COLORS.textLight}
              />
            )}
          </View>

          <Text style={styles.statusText}>
            {isRecording
              ? 'Recording...'
              : audioUri
              ? 'Recording Complete'
              : 'Tap to start recording'}
          </Text>
        </View>

        {/* Controls */}
        <View style={styles.controls}>
          {!audioUri ? (
            <TouchableOpacity
              style={[
                styles.recordButton,
                isRecording && styles.recordButtonActive,
              ]}
              onPress={isRecording ? stopRecording : startRecording}
            >
              <Ionicons
                name={isRecording ? 'stop' : 'mic'}
                size={32}
                color={COLORS.textWhite}
              />
            </TouchableOpacity>
          ) : (
            <View style={styles.actionButtons}>
              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={playRecording}
              >
                <Ionicons name="play" size={24} color={COLORS.primary} />
                <Text style={styles.secondaryButtonText}>Play</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={resetRecording}
              >
                <Ionicons name="refresh" size={24} color={COLORS.warning} />
                <Text style={styles.secondaryButtonText}>Re-record</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.primaryButton}
                onPress={submitRecording}
              >
                <Ionicons name="arrow-forward" size={24} color={COLORS.textWhite} />
                <Text style={styles.primaryButtonText}>Analyze</Text>
              </TouchableOpacity>
            </View>
          )}
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
    backgroundColor: COLORS.background,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  backButton: {
    marginRight: SPACING.md,
  },
  headerTitle: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  modeSelection: {
    padding: SPACING.lg,
    gap: SPACING.lg,
  },
  modeCard: {
    backgroundColor: COLORS.background,
    borderRadius: BORDER_RADIUS.lg,
    padding: SPACING.xl,
    alignItems: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  modeIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.primaryLight + '20',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.md,
  },
  modeTitle: {
    fontSize: FONT_SIZES.xl,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.sm,
  },
  modeDescription: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
    textAlign: 'center',
    marginBottom: SPACING.md,
  },
  modeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.xs,
    borderRadius: BORDER_RADIUS.round,
    backgroundColor: COLORS.primaryLight + '20',
  },
  modeBadgeText: {
    fontSize: FONT_SIZES.xs,
    fontWeight: '600',
    color: COLORS.primary,
  },
  recordingContent: {
    padding: SPACING.lg,
    gap: SPACING.lg,
  },
  textCard: {
    backgroundColor: COLORS.background,
    borderRadius: BORDER_RADIUS.lg,
    padding: SPACING.lg,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  textCategory: {
    fontSize: FONT_SIZES.xs,
    color: COLORS.primary,
    fontWeight: '600',
    textTransform: 'uppercase',
    marginBottom: SPACING.xs,
  },
  textTitle: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.md,
  },
  textScrollView: {
    maxHeight: 150,
    marginBottom: SPACING.md,
  },
  textContent: {
    fontSize: FONT_SIZES.md,
    color: COLORS.text,
    lineHeight: 24,
  },
  changeTextButton: {
    alignSelf: 'center',
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
  },
  changeTextButtonText: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.primary,
    fontWeight: '600',
  },
  instructionCard: {
    backgroundColor: COLORS.background,
    borderRadius: BORDER_RADIUS.lg,
    padding: SPACING.lg,
    alignItems: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  instructionTitle: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
    marginTop: SPACING.sm,
    marginBottom: SPACING.md,
  },
  instructionText: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
    lineHeight: 22,
  },
  visualizerCard: {
    backgroundColor: COLORS.background,
    borderRadius: BORDER_RADIUS.lg,
    padding: SPACING.xl,
    alignItems: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  timeDisplay: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: SPACING.lg,
  },
  timeText: {
    fontSize: FONT_SIZES.xxxl,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  timeLimit: {
    fontSize: FONT_SIZES.lg,
    color: COLORS.textLight,
    marginLeft: SPACING.xs,
  },
  waveformContainer: {
    height: 120,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.md,
  },
  waveformActive: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    height: 80,
  },
  waveBar: {
    width: 4,
    borderRadius: 2,
  },
  statusText: {
    fontSize: FONT_SIZES.md,
    color: COLORS.textLight,
  },
  controls: {
    alignItems: 'center',
  },
  recordButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  recordButtonActive: {
    backgroundColor: COLORS.error,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: SPACING.md,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
    borderRadius: BORDER_RADIUS.md,
    backgroundColor: COLORS.backgroundDark,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  secondaryButtonText: {
    fontSize: FONT_SIZES.md,
    color: COLORS.text,
    fontWeight: '600',
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    paddingHorizontal: SPACING.xl,
    paddingVertical: SPACING.md,
    borderRadius: BORDER_RADIUS.md,
    backgroundColor: COLORS.primary,
  },
  primaryButtonText: {
    fontSize: FONT_SIZES.md,
    color: COLORS.textWhite,
    fontWeight: 'bold',
  },
});
