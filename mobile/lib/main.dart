import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme.dart';
import 'features/auth/login_screen.dart';
import 'features/chat/chat_screen.dart';
import 'features/auth/auth_controller.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: MezaApp()));
}

class MezaApp extends ConsumerWidget {
  const MezaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    return MaterialApp(
      title: 'MEZA AI',
      debugShowCheckedModeBanner: false,
      theme: MezaTheme.light,
      home: auth.when(
        data: (session) =>
            session == null ? const LoginScreen() : const ChatScreen(),
        loading: () => const Scaffold(
          body: Center(child: CircularProgressIndicator()),
        ),
        error: (e, _) => LoginScreen(error: e.toString()),
      ),
    );
  }
}
