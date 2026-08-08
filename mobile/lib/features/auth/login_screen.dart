import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key, this.error});
  final String? error;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController(text: 'demo@meza.local');
  final _password = TextEditingController(text: 'meza12345');
  final _name = TextEditingController(text: 'MEZA Demo');
  bool _registerMode = false;
  String? _localError;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _name.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _localError = null);
    final auth = ref.read(authControllerProvider.notifier);
    try {
      if (_registerMode) {
        await auth.register(_email.text.trim(), _password.text, _name.text.trim());
      } else {
        await auth.login(_email.text.trim(), _password.text);
      }
    } catch (e) {
      setState(() => _localError = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final busy = auth.isLoading;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 48, 24, 24),
          children: [
            Text('MEZA AI', style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: const Color(0xFF1F3D2A),
                )),
            const SizedBox(height: 8),
            Text(
              _registerMode ? 'Создай аккаунт для чата' : 'Войди, чтобы продолжить чат',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 32),
            if (_registerMode) ...[
              TextField(
                controller: _name,
                decoration: const InputDecoration(labelText: 'Имя'),
              ),
              const SizedBox(height: 12),
            ],
            TextField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Email'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _password,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Пароль'),
            ),
            const SizedBox(height: 20),
            if (_localError != null || widget.error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _localError ?? widget.error!,
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            FilledButton(
              onPressed: busy ? null : _submit,
              child: Text(busy ? '...' : (_registerMode ? 'Зарегистрироваться' : 'Войти')),
            ),
            TextButton(
              onPressed: busy ? null : () => setState(() => _registerMode = !_registerMode),
              child: Text(_registerMode ? 'Уже есть аккаунт' : 'Создать аккаунт'),
            ),
          ],
        ),
      ),
    );
  }
}
