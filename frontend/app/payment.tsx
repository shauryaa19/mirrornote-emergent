import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from './context/AuthContext';
import { COLORS, SPACING, FONT_SIZES, BORDER_RADIUS } from './constants/theme';

export default function PaymentScreen() {
  const router = useRouter();
  const { updatePremiumStatus } = useAuth();
  const [selectedPlan, setSelectedPlan] = useState<'monthly' | 'yearly'>('yearly');
  const [processing, setProcessing] = useState(false);

  const plans = {
    monthly: {
      price: '₹499',
      period: 'month',
      savings: null,
    },
    yearly: {
      price: '₹3,999',
      period: 'year',
      savings: 'Save ₹2,000',
    },
  };

  const handlePayment = async () => {
    setProcessing(true);

    // Mock Razorpay payment - in production, integrate actual Razorpay
    setTimeout(() => {
      setProcessing(false);
      
      // Mock successful payment
      Alert.alert(
        'Payment Successful! 🎉',
        'You now have premium access to all features.',
        [
          {
            text: 'Continue',
            onPress: async () => {
              await updatePremiumStatus(true);
              router.replace('/(tabs)/dashboard');
            },
          },
        ]
      );
    }, 2000);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={COLORS.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Upgrade to Premium</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Premium Benefits */}
        <View style={styles.benefitsCard}>
          <View style={styles.premiumBadge}>
            <Ionicons name="star" size={32} color={COLORS.textWhite} />
          </View>
          <Text style={styles.benefitsTitle}>Unlock Premium Features</Text>
          
          <View style={styles.benefitsList}>
            <View style={styles.benefitItem}>
              <Ionicons name="checkmark-circle" size={24} color={COLORS.success} />
              <View style={styles.benefitContent}>
                <Text style={styles.benefitTitle}>Complete Training Program</Text>
                <Text style={styles.benefitDescription}>
                  Access all personalized training questions and exercises
                </Text>
              </View>
            </View>

            <View style={styles.benefitItem}>
              <Ionicons name="checkmark-circle" size={24} color={COLORS.success} />
              <View style={styles.benefitContent}>
                <Text style={styles.benefitTitle}>Unlimited Assessments</Text>
                <Text style={styles.benefitDescription}>
                  Record and analyze your voice as many times as you want
                </Text>
              </View>
            </View>

            <View style={styles.benefitItem}>
              <Ionicons name="checkmark-circle" size={24} color={COLORS.success} />
              <View style={styles.benefitContent}>
                <Text style={styles.benefitTitle}>Progress Tracking</Text>
                <Text style={styles.benefitDescription}>
                  Monitor your improvement over time with detailed analytics
                </Text>
              </View>
            </View>

            <View style={styles.benefitItem}>
              <Ionicons name="checkmark-circle" size={24} color={COLORS.success} />
              <View style={styles.benefitContent}>
                <Text style={styles.benefitTitle}>Advanced Insights</Text>
                <Text style={styles.benefitDescription}>
                  Get deeper analysis of your speaking patterns and style
                </Text>
              </View>
            </View>

            <View style={styles.benefitItem}>
              <Ionicons name="checkmark-circle" size={24} color={COLORS.success} />
              <View style={styles.benefitContent}>
                <Text style={styles.benefitTitle}>Priority Support</Text>
                <Text style={styles.benefitDescription}>
                  Get help faster with dedicated premium support
                </Text>
              </View>
            </View>
          </View>
        </View>

        {/* Plan Selection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Choose Your Plan</Text>
          
          <TouchableOpacity
            style={[
              styles.planCard,
              selectedPlan === 'yearly' && styles.planCardSelected,
            ]}
            onPress={() => setSelectedPlan('yearly')}
          >
            {selectedPlan === 'yearly' && (
              <View style={styles.popularBadge}>
                <Text style={styles.popularBadgeText}>BEST VALUE</Text>
              </View>
            )}
            <View style={styles.planHeader}>
              <View style={styles.radioButton}>
                {selectedPlan === 'yearly' && (
                  <View style={styles.radioButtonInner} />
                )}
              </View>
              <View style={styles.planInfo}>
                <Text style={styles.planName}>Yearly</Text>
                {plans.yearly.savings && (
                  <Text style={styles.planSavings}>{plans.yearly.savings}</Text>
                )}
              </View>
            </View>
            <View style={styles.planPricing}>
              <Text style={styles.planPrice}>{plans.yearly.price}</Text>
              <Text style={styles.planPeriod}>/{plans.yearly.period}</Text>
            </View>
            <Text style={styles.planNote}>
              Just ₹333/month - Save over 30%
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.planCard,
              selectedPlan === 'monthly' && styles.planCardSelected,
            ]}
            onPress={() => setSelectedPlan('monthly')}
          >
            <View style={styles.planHeader}>
              <View style={styles.radioButton}>
                {selectedPlan === 'monthly' && (
                  <View style={styles.radioButtonInner} />
                )}
              </View>
              <View style={styles.planInfo}>
                <Text style={styles.planName}>Monthly</Text>
              </View>
            </View>
            <View style={styles.planPricing}>
              <Text style={styles.planPrice}>{plans.monthly.price}</Text>
              <Text style={styles.planPeriod}>/{plans.monthly.period}</Text>
            </View>
          </TouchableOpacity>
        </View>

        {/* Payment Button */}
        <View style={styles.section}>
          <TouchableOpacity
            style={[styles.paymentButton, processing && styles.paymentButtonDisabled]}
            onPress={handlePayment}
            disabled={processing}
          >
            <Text style={styles.paymentButtonText}>
              {processing ? 'Processing...' : `Pay ${plans[selectedPlan].price}`}
            </Text>
            {!processing && (
              <Ionicons name="arrow-forward" size={20} color={COLORS.textWhite} />
            )}
          </TouchableOpacity>

          <Text style={styles.paymentNote}>
            🔒 Mock payment for demo purposes
          </Text>
          <Text style={styles.paymentNote}>
            In production, this would use Razorpay payment gateway
          </Text>
        </View>

        {/* Money Back Guarantee */}
        <View style={styles.guaranteeCard}>
          <Ionicons name="shield-checkmark" size={32} color={COLORS.primary} />
          <Text style={styles.guaranteeText}>
            7-Day Money Back Guarantee
          </Text>
          <Text style={styles.guaranteeSubtext}>
            Not satisfied? Get a full refund within 7 days
          </Text>
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
    justifyContent: 'space-between',
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
    backgroundColor: COLORS.background,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  backButton: {
    padding: SPACING.xs,
  },
  headerTitle: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  scrollContent: {
    paddingBottom: SPACING.xxl,
  },
  benefitsCard: {
    backgroundColor: COLORS.background,
    marginHorizontal: SPACING.lg,
    marginTop: SPACING.lg,
    borderRadius: BORDER_RADIUS.lg,
    padding: SPACING.xl,
    alignItems: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 8,
  },
  premiumBadge: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.md,
  },
  benefitsTitle: {
    fontSize: FONT_SIZES.xl,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.lg,
  },
  benefitsList: {
    alignSelf: 'stretch',
  },
  benefitItem: {
    flexDirection: 'row',
    marginBottom: SPACING.lg,
    gap: SPACING.md,
  },
  benefitContent: {
    flex: 1,
  },
  benefitTitle: {
    fontSize: FONT_SIZES.md,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: SPACING.xs,
  },
  benefitDescription: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
    lineHeight: 20,
  },
  section: {
    marginTop: SPACING.xl,
    paddingHorizontal: SPACING.lg,
  },
  sectionTitle: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: SPACING.md,
  },
  planCard: {
    backgroundColor: COLORS.background,
    borderRadius: BORDER_RADIUS.lg,
    padding: SPACING.lg,
    marginBottom: SPACING.md,
    borderWidth: 2,
    borderColor: COLORS.border,
    position: 'relative',
  },
  planCardSelected: {
    borderColor: COLORS.primary,
  },
  popularBadge: {
    position: 'absolute',
    top: -12,
    right: SPACING.lg,
    backgroundColor: COLORS.primary,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.xs,
    borderRadius: BORDER_RADIUS.round,
  },
  popularBadgeText: {
    fontSize: FONT_SIZES.xs,
    fontWeight: 'bold',
    color: COLORS.textWhite,
  },
  planHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.md,
    gap: SPACING.md,
  },
  radioButton: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioButtonInner: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: COLORS.primary,
  },
  planInfo: {
    flex: 1,
  },
  planName: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  planSavings: {
    fontSize: FONT_SIZES.xs,
    color: COLORS.success,
    fontWeight: '600',
    marginTop: SPACING.xs,
  },
  planPricing: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: SPACING.xs,
  },
  planPrice: {
    fontSize: FONT_SIZES.xxl,
    fontWeight: 'bold',
    color: COLORS.text,
  },
  planPeriod: {
    fontSize: FONT_SIZES.md,
    color: COLORS.textLight,
    marginLeft: SPACING.xs,
  },
  planNote: {
    fontSize: FONT_SIZES.xs,
    color: COLORS.textLight,
  },
  paymentButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.primary,
    paddingVertical: SPACING.md,
    borderRadius: BORDER_RADIUS.md,
    gap: SPACING.sm,
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  paymentButtonDisabled: {
    opacity: 0.6,
  },
  paymentButtonText: {
    fontSize: FONT_SIZES.lg,
    fontWeight: 'bold',
    color: COLORS.textWhite,
  },
  paymentNote: {
    fontSize: FONT_SIZES.xs,
    color: COLORS.textLight,
    textAlign: 'center',
    marginTop: SPACING.sm,
  },
  guaranteeCard: {
    backgroundColor: COLORS.background,
    marginHorizontal: SPACING.lg,
    marginTop: SPACING.xl,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.lg,
    alignItems: 'center',
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  guaranteeText: {
    fontSize: FONT_SIZES.md,
    fontWeight: 'bold',
    color: COLORS.text,
    marginTop: SPACING.sm,
  },
  guaranteeSubtext: {
    fontSize: FONT_SIZES.sm,
    color: COLORS.textLight,
    textAlign: 'center',
    marginTop: SPACING.xs,
  },
});
