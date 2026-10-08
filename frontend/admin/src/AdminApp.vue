<template>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark"><Hourglass /></span>
        时光迹
      </div>
      <div class="nav-label">平台管理</div>
      <nav class="nav" aria-label="管理导航">
        <button
          v-for="item in navItems"
          :key="item.view"
          type="button"
          :class="{ active: view === item.view }"
          :data-view="item.view"
          @click="show(item.view)"
        >
          <component :is="item.icon" />
          {{ item.label }}
        </button>
      </nav>
      <div class="sidebar-foot">时光迹 · 平台管理</div>
    </aside>

    <main class="main">
      <header class="topbar">
        <h1 id="page-title">{{ pageTitle }}</h1>
        <div class="topbar-right">
          <span class="prototype-label">平台管理</span>
          <button
            v-if="authed"
            class="button small"
            type="button"
            @click="logout"
          >
            退出
          </button>
          <span class="admin-name">平台管理员</span>
          <span class="avatar">管</span>
        </div>
      </header>

      <div class="content">
        <div v-if="loadError" class="load-notice" role="alert">
          {{ loadError }} <button class="button" @click="loadAll">重试</button>
        </div>
        <div v-if="loading" class="admin-loading" role="status">正在加载…</div>
        <!-- 总览 -->
        <section
          class="view"
          :class="{ active: view === 'dashboard' }"
          id="dashboard"
        >
          <div class="page-heading">
            <div>
              <h2>管理总览</h2>
              <p>{{ todayLabel }}</p>
            </div>
            <button
              class="button"
              type="button"
              data-view="reviews"
              @click="show('reviews')"
            >
              进入审核
              <ArrowRight />
            </button>
          </div>
          <div class="metrics" id="metrics">
            <div class="metric">
              <small>待处理举报</small>
              <strong class="critical">{{ stats.pending_reports }}</strong>
              <small>需要管理员核对</small>
            </div>
            <div class="metric">
              <small>已删除记录</small>
              <strong>{{ stats.removed_reports }}</strong>
              <small>演示数据累计</small>
            </div>
            <div class="metric">
              <small>平台用户</small>
              <strong>{{ stats.users }}</strong>
              <small>{{ stats.suspended_users }} 个已停用</small>
            </div>
            <div class="metric">
              <small>朋友圈</small>
              <strong>{{ stats.circles }}</strong>
              <small>{{ stats.pending_join_requests || 0 }} 个待审入圈申请</small>
            </div>
          </div>
          <div class="section-title">
            <h3>待处理举报</h3>
            <span class="count" id="dashboard-count"
              >{{ pendingReports.length }} 条待处理</span
            >
          </div>
          <div class="table-surface">
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>举报内容</th>
                    <th>所在朋友圈</th>
                    <th>举报原因</th>
                    <th>时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody id="dashboard-rows">
                  <tr v-for="item in pendingReports.slice(0, 5)" :key="item.id">
                    <td>
                      <div class="item-main">
                        <img
                          v-if="item.media_url"
                          class="thumb"
                          :src="item.media_url"
                          alt="举报记录缩略图"
                          loading="lazy"
                          decoding="async"
                        />
                        <span v-else class="thumb-placeholder">
                          <Video v-if="item.media_kind === 'video'" />
                          <FileText v-else />
                        </span>
                        <div>
                          <strong>记录 #{{ item.post_id }}</strong>
                          <small>{{ item.content }}</small>
                        </div>
                      </div>
                    </td>
                    <td>{{ item.circle_name }}</td>
                    <td>{{ item.type }}</td>
                    <td>{{ item.created }}</td>
                    <td>
                      <button
                        class="button small"
                        type="button"
                        @click="openReport(item.id)"
                      >
                        查看
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!pendingReports.length">
                    <td colspan="5" class="empty">暂无待处理举报</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- 内容审核 -->
        <section
          class="view"
          :class="{ active: view === 'reviews' }"
          id="reviews"
        >
          <div class="page-heading">
            <div>
              <h2>内容审核</h2>
              <p>按举报线索核对记录与图片、视频</p>
            </div>
            <span class="count" id="review-count"
              >{{ filteredReports.length }} 条记录</span
            >
          </div>
          <div class="toolbar">
            <div class="search">
              <Search />
              <input
                id="review-search"
                v-model="query"
                aria-label="搜索举报"
                placeholder="搜索文字、作者或圈名"
              />
            </div>
            <div class="segmented" aria-label="处理状态">
              <button
                v-for="f in filters"
                :key="f.id"
                type="button"
                :data-filter="f.id"
                :class="{ active: filter === f.id }"
                @click="filter = f.id"
              >
                {{ f.label }}
              </button>
            </div>
            <select
              id="review-category"
              v-model="category"
              aria-label="举报类型"
            >
              <option value="all">全部类型</option>
              <option value="骚扰辱骂">骚扰辱骂</option>
              <option value="隐私侵权">隐私侵权</option>
              <option value="广告引流">广告引流</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <div class="table-surface">
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>记录</th>
                    <th>作者 / 圈子</th>
                    <th>举报类型</th>
                    <th>提交时间</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody id="review-rows">
                  <tr v-for="item in filteredReports" :key="item.id">
                    <td>
                      <div class="item-main">
                        <img
                          v-if="item.media_url"
                          class="thumb"
                          :src="item.media_url"
                          alt="举报记录缩略图"
                          loading="lazy"
                          decoding="async"
                        />
                        <span v-else class="thumb-placeholder">
                          <Video v-if="item.media_kind === 'video'" />
                          <FileText v-else />
                        </span>
                        <div>
                          <strong>记录 #{{ item.post_id }}</strong>
                          <small>{{ item.content }}</small>
                        </div>
                      </div>
                    </td>
                    <td>
                      {{ item.author }}
                      <small>{{ item.circle_name }}</small>
                    </td>
                    <td>{{ item.type }}</td>
                    <td>{{ item.created }}</td>
                    <td>
                      <span class="badge" :class="item.status">{{
                        statusText[item.status]
                      }}</span>
                    </td>
                    <td>
                      <button
                        class="button small"
                        type="button"
                        @click="openReport(item.id)"
                      >
                        查看
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!filteredReports.length">
                    <td colspan="6" class="empty">没有符合条件的记录</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- 用户管理 -->
        <section class="view" :class="{ active: view === 'users' }" id="users">
          <div class="page-heading">
            <div>
              <h2>用户管理</h2>
              <p>查看账号状态和内容处置情况</p>
            </div>
            <span class="count" id="user-count"
              >{{ filteredUsers.length }} 位用户</span
            >
          </div>
          <div class="toolbar">
            <div class="search">
              <Search />
              <input
                id="user-search"
                v-model="userQuery"
                aria-label="搜索用户"
                placeholder="搜索用户名或昵称"
              />
            </div>
          </div>
          <div class="table-surface">
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>用户</th>
                    <th>加入的圈子</th>
                    <th>发布记录</th>
                    <th>被举报</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody id="user-rows">
                  <tr v-for="u in filteredUsers" :key="u.id">
                    <td>
                      <button
                        class="user-link"
                        type="button"
                        :title="`查看${u.nickname}的信息`"
                        @click="openUser(u.id)"
                      >
                        {{ u.nickname }}
                      </button>
                      <small>@{{ u.username }}</small>
                    </td>
                    <td>{{ (u.circles || []).length }}</td>
                    <td>{{ u.post_count }}</td>
                    <td>{{ reportedCountOf(u) }}</td>
                    <td>
                      <span class="badge" :class="u.status">{{
                        statusText[u.status]
                      }}</span>
                    </td>
                    <td>
                      <button
                        class="button small"
                        type="button"
                        @click="askUserAction(u.id)"
                      >
                        {{ u.status === 'active' ? '停用账号' : '恢复账号' }}
                      </button>
                      <button
                        class="button small danger"
                        type="button"
                        style="margin-left: 6px"
                        @click="askDeleteUser(u.id)"
                      >
                        删除账号
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!filteredUsers.length">
                    <td colspan="6" class="empty">没有找到用户</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- 朋友圈 -->
        <section
          class="view"
          :class="{ active: view === 'circles' }"
          id="circles"
        >
          <div class="page-heading">
            <div>
              <h2>朋友圈</h2>
              <p>查看圈子规模与待处理内容</p>
            </div>
            <span class="count" id="circle-count"
              >{{ circles.length }} 个圈子</span
            >
          </div>
          <div class="table-surface">
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>圈子</th>
                    <th>圈主</th>
                    <th>成员</th>
                    <th>管理员</th>
                    <th>入圈待审</th>
                    <th>记录</th>
                    <th>待处理举报</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody id="circle-rows">
                  <tr v-for="c in circles" :key="c.id">
                    <td>
                      <strong>{{ c.name }}</strong>
                      <small>{{ c.description }}</small>
                    </td>
                    <td>{{ c.owner }}</td>
                    <td>{{ c.members }}</td>
                    <td>{{ c.admins || 0 }}</td>
                    <td>{{ c.pending_join_requests || 0 }}</td>
                    <td>{{ c.posts }}</td>
                    <td>{{ pendingOfCircle(c.id) }}</td>
                    <td>
                      <button
                        class="button small"
                        type="button"
                        @click="openCircle(c.id)"
                      >
                        查看
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- 操作记录 -->
        <section class="view" :class="{ active: view === 'audit' }" id="audit">
          <div class="page-heading">
            <div>
              <h2>操作记录</h2>
              <p>内容与账号处置的管理员留痕</p>
            </div>
            <span class="count" id="audit-count"
              >{{ audit.length }} 条操作</span
            >
          </div>
          <div class="table-surface">
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>操作</th>
                    <th>对象</th>
                    <th>原因</th>
                    <th>操作人</th>
                  </tr>
                </thead>
                <tbody id="audit-rows">
                  <tr v-for="a in audit" :key="a.id">
                    <td>{{ a.time }}</td>
                    <td>{{ a.action }}</td>
                    <td>{{ a.target }}</td>
                    <td>{{ a.reason }}</td>
                    <td>{{ a.admin }}</td>
                  </tr>
                  <tr v-if="!audit.length">
                    <td colspan="5" class="empty">暂无操作记录</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>

  <!-- 审核抽屉 -->
  <div
    v-if="drawer.open"
    v-dialog="closeDrawer"
    class="overlay"
    :class="{ open: drawer.open }"
    id="drawer-layer"
    @click.self="closeDrawer"
  >
    <aside class="drawer" role="dialog" aria-modal="true" aria-label="审核详情">
      <div class="drawer-head">
        <div>
          <div class="eyebrow" id="drawer-eyebrow">{{ drawer.eyebrow }}</div>
          <h3 id="drawer-title">{{ drawer.title }}</h3>
        </div>
        <button
          class="icon-button"
          id="drawer-close"
          type="button"
          title="关闭"
          aria-label="关闭"
          @click="closeDrawer"
        >
          <X />
        </button>
      </div>
      <div class="drawer-body" id="drawer-body">
        <!-- 举报详情 -->
        <template v-if="drawer.kind === 'report' && drawer.data">
          <div>
            <span class="badge" :class="drawer.data.status">{{
              statusText[drawer.data.status]
            }}</span>
          </div>
          <div class="detail-grid">
            <div>
              <label>记录编号</label><strong>#{{ drawer.data.post_id }}</strong>
            </div>
            <div>
              <label>举报编号</label><strong>#{{ drawer.data.id }}</strong>
            </div>
            <div>
              <label>作者</label>
              <strong
                >{{ drawer.data.author }} (@{{ drawer.data.username }})</strong
              >
            </div>
            <div>
              <label>所在朋友圈</label
              ><strong>{{ drawer.data.circle_name }}</strong>
            </div>
            <div>
              <label>举报人</label><strong>{{ drawer.data.reporter }}</strong>
            </div>
            <div>
              <label>举报时间</label><strong>{{ drawer.data.created }}</strong>
            </div>
            <div>
              <label>生活日期</label
              ><strong>{{ drawer.data.event_date }}</strong>
            </div>
            <div>
              <label>举报类型</label><strong>{{ drawer.data.type }}</strong>
            </div>
          </div>
          <div class="detail-block">
            <h4>举报说明</h4>
            <p>{{ drawer.data.reason }}</p>
          </div>
          <div class="detail-block">
            <h4>记录内容</h4>
            <p>{{ drawer.data.content }}</p>
          </div>
          <div v-if="drawer.data.media?.length" class="detail-block">
            <h4>相关媒体 · {{ drawer.data.media.length }}</h4>
            <div class="evidence-grid">
              <button
                v-for="m in drawer.data.media"
                :key="m.id"
                class="evidence-button"
                :aria-label="m.kind === 'video' ? '预览视频' : '预览图片'"
                @click="evidence = m"
              >
                <MediaPreview :media="m" alt="举报证据" />
              </button>
            </div>
          </div>
          <p v-else-if="drawer.data.post_deleted" class="detail-block">
            原记录已删除，处理结果与文字记录已保留。
          </p>
        </template>

        <!-- 用户详情 -->
        <template v-else-if="drawer.kind === 'user' && drawer.data">
          <div>
            <span class="badge" :class="drawer.data.status">{{
              statusText[drawer.data.status]
            }}</span>
          </div>
          <div class="detail-grid">
            <div>
              <label>用户编号</label><strong>#{{ drawer.data.id }}</strong>
            </div>
            <div>
              <label>用户名</label><strong>@{{ drawer.data.username }}</strong>
            </div>
            <div>
              <label>昵称</label><strong>{{ drawer.data.nickname }}</strong>
            </div>
            <div>
              <label>注册日期</label
              ><strong>{{ drawer.data.joined_at }}</strong>
            </div>
            <div>
              <label>发布记录</label
              ><strong>{{ drawer.data.post_count }} 条</strong>
            </div>
            <div>
              <label>被举报记录</label>
              <strong>{{ relatedReportsOfUser(drawer.data).length }} 条</strong>
            </div>
          </div>
          <div class="detail-block">
            <h4>所属朋友圈</h4>
            <p v-for="name in drawer.data.circles || []" :key="name">
              {{ name }}
            </p>
          </div>
          <div class="detail-block">
            <h4>相关举报</h4>
            <template v-if="relatedReportsOfUser(drawer.data).length">
              <p
                v-for="item in relatedReportsOfUser(drawer.data)"
                :key="item.id"
                style="margin: 0 0 10px"
              >
                <button
                  class="button text"
                  type="button"
                  @click="openReport(item.id)"
                >
                  记录 #{{ item.post_id }} · {{ item.type }} ·
                  {{ statusText[item.status] }}
                </button>
              </p>
            </template>
            <p v-else>暂无举报</p>
          </div>
        </template>

        <!-- 圈子详情 -->
        <template v-else-if="drawer.kind === 'circle' && drawer.data">
          <div class="detail-grid">
            <div>
              <label>圈主</label><strong>{{ drawer.data.owner }}</strong>
            </div>
            <div>
              <label>成员</label><strong>{{ drawer.data.members }} 位</strong>
            </div>
            <div>
              <label>记录</label><strong>{{ drawer.data.posts }} 条</strong>
            </div>
            <div>
              <label>待处理举报</label>
              <strong>{{ pendingOfCircle(drawer.data.id) }} 条</strong>
            </div>
          </div>
          <div class="detail-block">
            <h4>圈子简介</h4>
            <p>{{ drawer.data.description || '无' }}</p>
          </div>
          <div class="detail-block">
            <h4>相关举报</h4>
            <template v-if="relatedReportsOfCircle(drawer.data.id).length">
              <p
                v-for="item in relatedReportsOfCircle(drawer.data.id)"
                :key="item.id"
                style="margin: 0 0 10px"
              >
                <button
                  class="button text"
                  type="button"
                  @click="openReport(item.id)"
                >
                  #{{ item.id }} · {{ item.type }} ·
                  {{ statusText[item.status] }}
                </button>
              </p>
            </template>
            <p v-else>暂无举报</p>
          </div>
        </template>
      </div>
      <div class="drawer-actions" id="drawer-actions">
        <template
          v-if="drawer.kind === 'report' && drawer.data?.status === 'pending'"
        >
          <button
            class="button"
            type="button"
            @click="askAction('dismiss', drawer.data.id)"
          >
            <Check />
            驳回举报
          </button>
          <button
            class="button danger"
            type="button"
            @click="askAction('remove', drawer.data.id)"
          >
            <Trash2 />
            删除内容
          </button>
        </template>
        <span v-else-if="drawer.kind === 'report'" class="count"
          >此举报已处理</span
        >
        <button
          v-else-if="drawer.kind === 'user'"
          class="button"
          :class="drawer.data.status === 'active' ? 'danger' : 'primary'"
          type="button"
          @click="askUserAction(drawer.data.id)"
        >
          <UserX v-if="drawer.data.status === 'active'" />
          <UserCheck v-else />
          {{ drawer.data.status === 'active' ? '停用账号' : '恢复账号' }}
        </button>
        <button
          v-if="drawer.kind === 'user'"
          class="button danger"
          type="button"
          @click="askDeleteUser(drawer.data.id)"
        >
          <Trash2 />
          删除账号
        </button>
        <span v-else class="count">平台管理员可从相关举报进入审核</span>
      </div>
    </aside>
  </div>

  <!-- 确认操作 -->
  <div
    v-if="modal.open"
    v-dialog="closeModal"
    class="modal-layer open"
    id="modal-layer"
    @click.self="closeModal"
  >
    <form
      class="modal"
      id="action-form"
      role="dialog"
      aria-modal="true"
      aria-label="确认操作"
      @submit.prevent="completeAction"
    >
      <div class="modal-head">
        <h3 id="modal-title">{{ modal.title }}</h3>
        <button
          class="icon-button"
          id="modal-close"
          type="button"
          title="关闭"
          @click="closeModal"
        >
          <X />
        </button>
      </div>
      <div class="modal-content">
        <p id="modal-description">{{ modal.description }}</p>
        <div class="field">
          <label for="action-reason">处理原因</label>
          <select id="action-reason" v-model="modal.reason" required>
            <option value="">请选择原因</option>
            <option v-for="o in modal.options" :key="o" :value="o">
              {{ o }}
            </option>
          </select>
        </div>
        <div class="field">
          <label for="action-note">补充说明</label>
          <textarea
            id="action-note"
            v-model="modal.note"
            placeholder="可选，供操作记录留存"
          ></textarea>
        </div>
      </div>
      <div class="modal-actions">
        <button
          class="button"
          id="modal-cancel"
          type="button"
          @click="closeModal"
        >
          取消
        </button>
        <button
          id="modal-submit"
          class="button"
          :class="modal.danger ? 'danger' : 'primary'"
          type="submit"
          :disabled="actionBusy || !modal.reason"
        >
          {{ actionBusy ? '处理中…' : modal.button }}
        </button>
      </div>
    </form>
  </div>

  <!-- 未登录 -->
  <div class="modal-layer" :class="{ open: !authed && ready }" id="login-layer">
    <form class="modal" @submit.prevent="login">
      <div class="modal-head">
        <h3>管理后台登录</h3>
      </div>
      <div class="modal-content">
        <p>请使用平台管理员账号进入</p>
        <div class="field">
          <label>用户名</label>
          <input v-model="loginForm.username" class="field-input" required />
        </div>
        <div class="field">
          <label>密码</label>
          <input
            v-model="loginForm.password"
            type="password"
            class="field-input"
            required
          />
        </div>
        <p v-if="loginError" style="color: var(--red)">{{ loginError }}</p>
      </div>
      <div class="modal-actions">
        <button class="button primary" type="submit">登录</button>
      </div>
    </form>
  </div>

  <div id="toast" :class="{ show: !!toast }" role="status" aria-live="polite">
    {{ toast }}
  </div>
  <div
    v-if="evidence"
    v-dialog="closeEvidence"
    class="modal-layer open evidence-layer"
    @click.self="closeEvidence"
  >
    <section class="evidence-viewer">
      <button
        class="icon-button"
        title="关闭预览"
        aria-label="关闭预览"
        @click="closeEvidence"
      >
        <X /></button
      ><video
        v-if="evidence.kind === 'video'"
        ref="evidenceVideo"
        :src="evidence.original_url"
        :poster="evidence.preview_url || undefined"
        controls
        playsinline
        preload="metadata"
        @error="evidenceError = true"
      /><img
        v-else
        :src="evidence.original_url"
        alt="完整举报证据"
        @error="evidenceError = true"
      />
      <p v-if="evidenceError">媒体无法预览，可下载查看。</p>
      <a class="button" :href="evidence.download_url">下载原文件</a>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import MediaPreview from '../../user/src/components/MediaPreview.vue'
import { dialogDirective as vDialog } from '../../user/src/utils/dialog'
import {
  ArrowRight,
  Check,
  CircleDot,
  FileText,
  History,
  Hourglass,
  LayoutDashboard,
  Search,
  ShieldCheck,
  Trash2,
  UserCheck,
  UsersRound,
  UserX,
  Video,
  X,
} from 'lucide-vue-next'
import api from './api'

const ready = ref(false)
const authed = ref(false)
const loginForm = reactive({ username: 'admin', password: 'admin123' })
const loginError = ref('')
const view = ref('dashboard')
const toast = ref('')
const loading = ref(false),
  loadError = ref(''),
  actionBusy = ref(false),
  evidence = ref(null),
  evidenceError = ref(false),
  evidenceVideo = ref(null)
const debouncedQuery = ref(''),
  debouncedUserQuery = ref('')
let queryTimer, userQueryTimer, toastTimer

const stats = ref({
  pending_reports: 0,
  removed_reports: 0,
  users: 0,
  suspended_users: 0,
  circles: 0,
})
const reports = ref([])
const users = ref([])
const circles = ref([])
const audit = ref([])
const filter = ref('pending')
const category = ref('all')
const query = ref('')
const userQuery = ref('')
watch(query, (v) => {
  clearTimeout(queryTimer)
  queryTimer = setTimeout(() => (debouncedQuery.value = v), 250)
})
watch(userQuery, (v) => {
  clearTimeout(userQueryTimer)
  userQueryTimer = setTimeout(() => (debouncedUserQuery.value = v), 250)
})

const drawer = reactive({
  open: false,
  kind: '',
  data: null,
  eyebrow: '',
  title: '',
})
const modal = reactive({
  open: false,
  kind: '',
  id: null,
  title: '',
  description: '',
  options: [],
  reason: '',
  note: '',
  button: '',
  danger: false,
})

const navItems = [
  { view: 'dashboard', label: '总览', icon: LayoutDashboard },
  { view: 'reviews', label: '内容审核', icon: ShieldCheck },
  { view: 'users', label: '用户管理', icon: UsersRound },
  { view: 'circles', label: '朋友圈', icon: CircleDot },
  { view: 'audit', label: '操作记录', icon: History },
]
const filters = [
  { id: 'pending', label: '待处理' },
  { id: 'all', label: '全部' },
  { id: 'removed', label: '已删除' },
  { id: 'dismissed', label: '已驳回' },
]
const statusText = {
  pending: '待处理',
  removed: '已删除',
  dismissed: '已驳回',
  active: '正常',
  suspended: '已停用',
}

const pageTitle = computed(
  () =>
    ({
      dashboard: '管理总览',
      reviews: '内容审核',
      users: '用户管理',
      circles: '朋友圈',
      audit: '操作记录',
    })[view.value] || '管理总览',
)

const todayLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
})

const pendingReports = computed(() =>
  reports.value.filter((r) => r.status === 'pending'),
)

const filteredReports = computed(() => {
  const q = debouncedQuery.value.trim().toLowerCase()
  return reports.value.filter(
    (item) =>
      (filter.value === 'all' || item.status === filter.value) &&
      (category.value === 'all' || item.type === category.value) &&
      (!q ||
        [
          item.content,
          item.author,
          item.username,
          item.circle_name,
          String(item.post_id),
        ].some((v) => String(v).toLowerCase().includes(q))),
  )
})

const filteredUsers = computed(() => {
  const q = debouncedUserQuery.value.trim().toLowerCase()
  return users.value.filter(
    (u) =>
      !q ||
      u.username.toLowerCase().includes(q) ||
      u.nickname.toLowerCase().includes(q),
  )
})

function reportedCountOf(u) {
  return reports.value.filter((r) => r.username === u.username).length
}
function pendingOfCircle(id) {
  return reports.value.filter(
    (r) => r.circle_id === id && r.status === 'pending',
  ).length
}
function relatedReportsOfUser(u) {
  return reports.value.filter((r) => r.username === u.username)
}
function relatedReportsOfCircle(id) {
  return reports.value.filter((r) => r.circle_id === id)
}

function show(next) {
  view.value = next
  window.scrollTo(0, 0)
}

function notice(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = ''
  }, 2600)
}

async function login() {
  loginError.value = ''
  try {
    const { data } = await api.post('/api/admin/auth/login', {
      username: loginForm.username.trim(),
      password: loginForm.password,
    })
    if (!data.is_admin) {
      await api.post('/api/admin/auth/logout')
      loginError.value = '该账号不是平台管理员'
      return
    }
    authed.value = true
    await loadAll()
    notice('已登录平台管理后台')
  } catch (e) {
    loginError.value = e.userMessage || '登录失败'
  }
}

async function logout() {
  await api.post('/api/admin/auth/logout')
  authed.value = false
}

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const [s, r, u, c, a] = await Promise.all([
      api.get('/api/admin/stats'),
      api.get('/api/admin/reports', { params: { status: 'all' } }),
      api.get('/api/admin/users'),
      api.get('/api/admin/circles'),
      api.get('/api/admin/audit'),
    ])
    stats.value = s.data
    reports.value = r.data
    users.value = u.data
    circles.value = c.data
    audit.value = a.data
  } catch (e) {
    loadError.value = e.userMessage || '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

function openReport(id) {
  const item = reports.value.find((r) => r.id === Number(id))
  if (!item) return
  drawer.open = true
  drawer.kind = 'report'
  drawer.data = item
  drawer.eyebrow = '内容审核'
  drawer.title = `记录 #${item.post_id}`
}

function openUser(id) {
  const u = users.value.find((x) => x.id === Number(id))
  if (!u) return
  drawer.open = true
  drawer.kind = 'user'
  drawer.data = u
  drawer.eyebrow = '用户信息'
  drawer.title = u.nickname
}

function openCircle(id) {
  const c = circles.value.find((x) => x.id === Number(id))
  if (!c) return
  drawer.open = true
  drawer.kind = 'circle'
  drawer.data = c
  drawer.eyebrow = '朋友圈'
  drawer.title = c.name
}

function closeDrawer() {
  drawer.open = false
  drawer.data = null
}

function askAction(kind, id) {
  const item = reports.value.find((r) => r.id === Number(id))
  if (!item) return
  const meta = {
    remove: {
      title: '删除这条记录',
      description: '删除后，这条记录及相关媒体将不再出现在用户端。',
      options: ['骚扰辱骂', '隐私侵权', '广告引流', '其他'],
      button: '确认删除',
      danger: true,
    },
    dismiss: {
      title: '驳回这条举报',
      description: '确认内容无违规后，举报状态将改为已驳回。',
      options: ['未发现违规', '信息不足', '重复举报', '其他'],
      button: '确认驳回',
      danger: false,
    },
  }[kind]
  modal.open = true
  modal.kind = kind
  modal.id = Number(id)
  modal.title = meta.title
  modal.description = meta.description
  modal.options = meta.options
  modal.reason = ''
  modal.note = ''
  modal.button = meta.button
  modal.danger = meta.danger
}

function askUserAction(id) {
  const u = users.value.find((x) => x.id === Number(id))
  if (!u) return
  const kind = u.status === 'active' ? 'suspend' : 'restore'
  const meta = {
    suspend: {
      title: '停用用户账号',
      description: `停用 ${u.nickname} 的账号后，该账号将不能继续使用。`,
      options: ['多次发布违规内容', '骚扰其他用户', '异常账号行为', '其他'],
      button: '确认停用',
      danger: true,
    },
    restore: {
      title: '恢复用户账号',
      description: `恢复 ${u.nickname} 的账号使用。`,
      options: ['复核通过', '申诉通过', '其他'],
      button: '确认恢复',
      danger: false,
    },
  }[kind]
  modal.open = true
  modal.kind = kind
  modal.id = Number(id)
  modal.title = meta.title
  modal.description = meta.description
  modal.options = meta.options
  modal.reason = ''
  modal.note = ''
  modal.button = meta.button
  modal.danger = meta.danger
}

function askDeleteUser(id) {
  const u = users.value.find((x) => x.id === Number(id))
  if (!u) return
  if (u.is_admin) {
    notice('不能删除管理员账号')
    return
  }
  modal.open = true
  modal.kind = 'delete_user'
  modal.id = Number(id)
  modal.title = '永久删除账号'
  modal.description = `将删除 ${u.nickname}（@${u.username}）及其全部记录、照片视频和评论，不可恢复。`
  modal.options = ['账号违规', '用户申请注销', '测试数据清理', '其他']
  modal.reason = ''
  modal.note = ''
  modal.button = '确认删除账号'
  modal.danger = true
}

function closeModal() {
  if (actionBusy.value) return
  modal.open = false
}

async function completeAction() {
  if (!modal.reason || actionBusy.value) return
  actionBusy.value = true
  const payload = { reason: modal.reason, note: modal.note.trim() }
  let action = ''
  try {
    if (modal.kind === 'remove') {
      await api.post(`/api/admin/reports/${modal.id}/remove`, payload)
      action = '删除记录'
    } else if (modal.kind === 'dismiss') {
      await api.post(`/api/admin/reports/${modal.id}/dismiss`, payload)
      action = '驳回举报'
    } else if (modal.kind === 'suspend') {
      await api.post(`/api/admin/users/${modal.id}/suspend`, payload)
      action = '停用账号'
    } else if (modal.kind === 'restore') {
      await api.post(`/api/admin/users/${modal.id}/restore`, payload)
      action = '恢复账号'
    } else if (modal.kind === 'delete_user') {
      await api.delete(`/api/admin/users/${modal.id}`, { data: payload })
      action = '删除账号'
      closeDrawer()
    }
    modal.open = false
    await loadAll()
    if (drawer.open && drawer.kind === 'report') {
      const updated = reports.value.find((r) => r.id === drawer.data?.id)
      if (updated) openReport(updated.id)
    } else if (drawer.open && drawer.kind === 'user') {
      const updated = users.value.find((u) => u.id === drawer.data?.id)
      if (updated) openUser(updated.id)
    }
    notice(`${action}已记录在操作日志中`)
  } catch (e) {
    notice(e.userMessage || '操作失败')
  } finally {
    actionBusy.value = false
  }
}
function closeEvidence() {
  evidenceVideo.value?.pause()
  evidence.value = null
  evidenceError.value = false
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    if (modal.open) closeModal()
    else if (drawer.open) closeDrawer()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  try {
    const { data } = await api.get('/api/admin/auth/me')
    if (data.is_admin) {
      authed.value = true
      await loadAll()
    }
  } catch {
    /* login layer */
  } finally {
    ready.value = true
  }
})

onBeforeUnmount(() => {
  clearTimeout(queryTimer)
  clearTimeout(userQueryTimer)
  clearTimeout(toastTimer)
  window.removeEventListener('keydown', onKeydown)
})
</script>
