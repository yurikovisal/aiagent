import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../auth/auth_controller.dart';

class ChatMessage {
  ChatMessage({required this.role, required this.content});
  final String role;
  String content;
}

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _input = TextEditingController();
  final _messages = <ChatMessage>[];
  String? _conversationId;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _ensureConversation();
  }

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _ensureConversation() async {
    final conv = await apiClient.post('/api/v1/chat/conversations', {
      'title': 'Мобильный чат',
    });
    setState(() => _conversationId = conv['id'] as String);
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _conversationId == null || _sending) return;
    setState(() {
      _sending = true;
      _messages.add(ChatMessage(role: 'user', content: text));
      _messages.add(ChatMessage(role: 'assistant', content: ''));
      _input.clear();
    });
    try {
      await for (final token in apiClient.streamChat(_conversationId!, text)) {
        setState(() => _messages.last.content += token);
      }
    } catch (e) {
      setState(() => _messages.last.content = 'Ошибка: $e');
    } finally {
      setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MEZA AI'),
        actions: [
          IconButton(
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                final isUser = msg.role == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 10),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    constraints: BoxConstraints(
                      maxWidth: MediaQuery.of(context).size.width * 0.8,
                    ),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFFC56A2D) : Colors.white,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(
                      msg.content.isEmpty && !isUser ? '...' : msg.content,
                      style: TextStyle(color: isUser ? Colors.white : const Color(0xFF142018)),
                    ),
                  ),
                );
              },
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      minLines: 1,
                      maxLines: 4,
                      decoration: const InputDecoration(hintText: 'Спроси про склад, МАФ, план...'),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _sending ? null : _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
