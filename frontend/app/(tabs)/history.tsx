import { View, Text, StyleSheet, SafeAreaView } from 'react-native';
import { COLORS, SPACING, FONT_SIZES } from '../constants/theme';

export default function HistoryScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Assessment History</Text>
        <Text style={styles.emptyText}>No assessments yet</Text>
        <Text style={styles.emptySubtext}>
          Start your first assessment to see your history here
        </Text>
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
    paddingTop: SPACING.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: FONT_SIZES.xxl,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.xxl,
    position: 'absolute',
    top: SPACING.lg,
  },
  emptyText: {
    fontSize: FONT_SIZES.lg,
    color: COLORS.textLight,
    marginBottom: SPACING.sm,
  },
  emptySubtext: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
    textAlign: 'center',
  },
});
