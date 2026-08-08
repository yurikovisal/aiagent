import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiClient {
  ApiClient({this.baseUrl = const String.fromEnvironment(
    'MEZA_API_BASE',
    defaultValue: 'http://10.0.2.2:8000',
  )});

  final String baseUrl;
  String? accessToken;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (accessToken != null) 'Authorization': 'Bearer $accessToken',
      };

  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    final res = await http.post(_uri(path), headers: _headers, body: jsonEncode(body));
    return _decode(res);
  }

  Future<Map<String, dynamic>> getMap(String path) async {
    final res = await http.get(_uri(path), headers: _headers);
    return _decode(res);
  }

  Future<List<dynamic>> getList(String path) async {
    final res = await http.get(_uri(path), headers: _headers);
    if (res.statusCode >= 400) {
      throw Exception('HTTP ${res.statusCode}: ${res.body}');
    }
    return jsonDecode(res.body) as List<dynamic>;
  }

  Stream<String> streamChat(String conversationId, String content) async* {
    final request = http.Request(
      'POST',
      _uri('/api/v1/chat/conversations/$conversationId/messages'),
    );
    request.headers.addAll(_headers);
    request.body = jsonEncode({'content': content, 'stream': true});
    final response = await request.send();
    if (response.statusCode >= 400) {
      throw Exception('Stream failed: ${response.statusCode}');
    }
    await for (final chunk in response.stream.transform(utf8.decoder)) {
      for (final line in chunk.split('\n')) {
        if (!line.startsWith('data: ')) continue;
        final raw = line.substring(6).trim();
        if (raw.isEmpty) continue;
        final data = jsonDecode(raw) as Map<String, dynamic>;
        if (data['done'] == true) return;
        final token = data['token'];
        if (token is String) yield token;
      }
    }
  }

  Map<String, dynamic> _decode(http.Response res) {
    if (res.statusCode >= 400) {
      throw Exception('HTTP ${res.statusCode}: ${res.body}');
    }
    if (res.body.isEmpty) return {};
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}

final apiClient = ApiClient();
