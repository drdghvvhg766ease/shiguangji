<template>
  <div class="story-caption">
    <div class="story-byline">
      <span>{{ post.nickname || post.username }}</span
      ><span
        >{{ post.event_date }}
        <template v-if="post.activity_tag"
          >· {{ post.activity_tag }}</template
        ></span
      >
    </div>
    <p>{{ post.content || '这一刻，没有文字。' }}</p>
    <button
      class="text-button story-comment"
      title="打开评论"
      @click="$emit('open', $event)"
    >
      <MessageCircle :size="15" />{{ post.comment_count }}
    </button>
  </div>
</template>
<script setup>
import { MessageCircle } from 'lucide-vue-next'
defineProps({ post: { type: Object, required: true } })
defineEmits(['open'])
</script>
