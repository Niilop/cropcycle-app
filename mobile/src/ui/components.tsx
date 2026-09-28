import { MaterialCommunityIcons } from '@expo/vector-icons'
import { useState, type ComponentProps, type ReactNode } from 'react'
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from 'react-native'

import { colors, radius, space, touch } from './theme'

type IconName = ComponentProps<typeof MaterialCommunityIcons>['name']

interface ButtonProps {
  label: string
  onPress: () => void
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  icon?: IconName
  disabled?: boolean
  busy?: boolean
  compact?: boolean
  accessibilityLabel?: string
  style?: ViewStyle
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  icon,
  disabled,
  busy,
  compact,
  accessibilityLabel,
  style,
}: ButtonProps) {
  const palette = {
    primary: { bg: colors.primary, fg: colors.primaryText, border: colors.primary },
    secondary: { bg: colors.surface, fg: colors.primary, border: colors.border },
    danger: { bg: colors.dangerSoft, fg: colors.danger, border: colors.dangerSoft },
    ghost: { bg: 'transparent', fg: colors.primary, border: 'transparent' },
  }[variant]
  const inactive = disabled || busy
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ disabled: !!inactive, busy: !!busy }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        compact && styles.compact,
        { backgroundColor: palette.bg, borderColor: palette.border },
        pressed && styles.pressed,
        inactive && styles.disabled,
        style,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={palette.fg} />
      ) : (
        icon && <MaterialCommunityIcons name={icon} size={20} color={palette.fg} />
      )}
      {!!label && <Text style={[styles.buttonText, { color: palette.fg }]}>{label}</Text>}
    </Pressable>
  )
}

export function IconButton({
  icon,
  label,
  onPress,
  disabled,
}: {
  icon: IconName
  label: string
  onPress: () => void
  disabled?: boolean
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      onPress={onPress}
      hitSlop={4}
      style={({ pressed }) => [
        styles.iconButton,
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      <MaterialCommunityIcons name={icon} size={26} color={colors.text} />
    </Pressable>
  )
}

export function Field({
  label,
  hint,
  ...input
}: TextInputProps & { label: string; hint?: string }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.muted}
        style={styles.input}
        {...input}
      />
      {!!hint && <Text style={styles.hint}>{hint}</Text>}
    </View>
  )
}

export function Chip({
  label,
  selected,
  onPress,
  color,
}: {
  label: string
  selected?: boolean
  onPress: () => void
  color?: string
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: !!selected }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        color ? { backgroundColor: color } : null,
        selected && styles.chipSelected,
        pressed && styles.pressed,
      ]}
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
  )
}

/** Numeric value with − / + buttons and a text field, for tap-first editing (D011). */
export function Stepper({
  label,
  value,
  step,
  min,
  onChange,
}: {
  label: string
  value: number
  step: number
  min?: number
  onChange: (value: number) => void
}) {
  // Shows the typed text only while editing; otherwise the current value.
  const [draft, setDraft] = useState<string | null>(null)
  const clamp = (next: number) => (min === undefined ? next : Math.max(min, next))
  const commit = () => {
    if (draft === null) return
    const parsed = Number(draft.replace(',', '.'))
    setDraft(null)
    if (draft.trim() && Number.isFinite(parsed) && clamp(parsed) !== value) onChange(clamp(parsed))
  }
  return (
    <View style={styles.stepper}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.stepperRow}>
        <IconButton
          icon="minus"
          label={`${label} −`}
          onPress={() => onChange(clamp(value - step))}
        />
        <TextInput
          accessibilityLabel={label}
          keyboardType="decimal-pad"
          value={draft ?? String(value)}
          onChangeText={setDraft}
          onBlur={commit}
          onSubmitEditing={commit}
          style={[styles.input, styles.stepperInput]}
        />
        <IconButton
          icon="plus"
          label={`${label} +`}
          onPress={() => onChange(clamp(value + step))}
        />
      </View>
    </View>
  )
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <Text accessibilityRole="header" style={styles.sectionTitle}>
      {children}
    </Text>
  )
}

export function Muted({ children }: { children: ReactNode }) {
  return <Text style={styles.muted}>{children}</Text>
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View accessibilityRole="alert" style={styles.error}>
      <Text style={styles.errorText}>{message}</Text>
      {onRetry && <Button label="↻" variant="ghost" compact onPress={onRetry} />}
    </View>
  )
}

export function Loading({ label }: { label: string }) {
  return (
    <View style={styles.loading} accessibilityLabel={label}>
      <ActivityIndicator size="large" color={colors.primary} />
    </View>
  )
}

const styles = StyleSheet.create({
  button: {
    minHeight: touch,
    paddingHorizontal: space.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.sm,
  },
  compact: { paddingHorizontal: space.md },
  buttonText: { fontSize: 16, fontWeight: '600' },
  pressed: { opacity: 0.75 },
  disabled: { opacity: 0.45 },
  iconButton: {
    width: touch,
    height: touch,
    borderRadius: touch / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  field: { gap: space.xs },
  label: { fontSize: 14, fontWeight: '600', color: colors.muted },
  hint: { fontSize: 13, color: colors.muted },
  input: {
    minHeight: touch,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    fontSize: 17,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  chip: {
    minHeight: 40,
    paddingHorizontal: space.md,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    justifyContent: 'center',
  },
  chipSelected: { borderColor: colors.primary, borderWidth: 2 },
  chipText: { fontSize: 15, color: colors.text },
  chipTextSelected: { fontWeight: '700', color: colors.primary },
  stepper: { gap: space.xs, flexGrow: 1, flexBasis: 150 },
  stepperRow: { flexDirection: 'row', alignItems: 'center', gap: space.xs },
  stepperInput: { flex: 1, minWidth: 64, textAlign: 'center' },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: colors.text, marginTop: space.md },
  muted: { fontSize: 15, color: colors.muted },
  error: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    padding: space.md,
    borderRadius: radius.md,
    backgroundColor: colors.dangerSoft,
  },
  errorText: { flex: 1, color: colors.danger, fontSize: 15 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: space.xl },
})

export function YearSwitch({
  year,
  onChange,
  previousLabel,
  nextLabel,
}: {
  year: number
  onChange: (year: number) => void
  previousLabel: string
  nextLabel: string
}) {
  return (
    <View style={yearStyles.row}>
      <IconButton icon="chevron-left" label={previousLabel} onPress={() => onChange(year - 1)} />
      <Text accessibilityRole="text" style={yearStyles.year} testID="year">
        {year}
      </Text>
      <IconButton icon="chevron-right" label={nextLabel} onPress={() => onChange(year + 1)} />
    </View>
  )
}

const yearStyles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  year: { fontSize: 20, fontWeight: '700', color: colors.text, minWidth: 56, textAlign: 'center' },
})
