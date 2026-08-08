import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';

class AuthSession {
  AuthSession({required this.accessToken, required this.refreshToken, required this.email});
  final String accessToken;
  final String refreshToken;
  final String email;
}

class AuthController extends AsyncNotifier<AuthSession?> {
  @override
  Future<AuthSession?> build() async => null;

  Future<void> login(String email, String password) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final tokens = await apiClient.post('/api/v1/auth/login', {
        'email': email,
        'password': password,
      });
      apiClient.accessToken = tokens['access_token'] as String;
      return AuthSession(
        accessToken: tokens['access_token'] as String,
        refreshToken: tokens['refresh_token'] as String,
        email: email,
      );
    });
  }

  Future<void> register(String email, String password, String fullName) async {
    await apiClient.post('/api/v1/auth/register', {
      'email': email,
      'password': password,
      'full_name': fullName,
    });
    await login(email, password);
  }

  Future<void> logout() async {
    final session = state.valueOrNull;
    if (session != null) {
      try {
        await apiClient.post('/api/v1/auth/logout', {
          'refresh_token': session.refreshToken,
        });
      } catch (_) {}
    }
    apiClient.accessToken = null;
    state = const AsyncData(null);
  }
}

final authControllerProvider =
    AsyncNotifierProvider<AuthController, AuthSession?>(AuthController.new);
