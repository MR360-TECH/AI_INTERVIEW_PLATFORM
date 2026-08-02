import json
import os

# Define the complete set of questions for all companies
COMPANY_QUESTIONS = {
    "google": {
        "name": "Google",
        "color": "#4285F4",
        "description": "Google interviews place an exceptionally heavy emphasis on algorithmic efficiency, data structures, and distributed systems scaling.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Find the Median of two sorted arrays",
                        "difficulty": "Hard",
                        "tags": ["Array", "Binary Search", "Divide & Conquer"],
                        "frequency": "High",
                        "question": "Given two sorted arrays nums1 and nums2 of size m and n respectively, return the median of the two sorted arrays. The overall run time complexity should be O(log (m+n)).",
                        "answer": "To achieve O(log(m+n)) complexity, we perform binary search. Instead of merging, we partition both arrays such that the left side contains half of the total elements, and all elements on the left are less than or equal to elements on the right.",
                        "solutions": {
                            "python": "def findMedianSortedArrays(nums1, nums2):\n    # Ensure nums1 is the shorter array\n    if len(nums1) > len(nums2):\n        nums1, nums2 = nums2, nums1\n    x, y = len(nums1), len(nums2)\n    low, high = 0, x\n    while low <= high:\n        partitionX = (low + high) // 2\n        partitionY = (x + y + 1) // 2 - partitionX\n        maxLeftX = float('-inf') if partitionX == 0 else nums1[partitionX - 1]\n        minRightX = float('inf') if partitionX == x else nums1[partitionX]\n        maxLeftY = float('-inf') if partitionY == 0 else nums2[partitionY - 1]\n        minRightY = float('inf') if partitionY == y else nums2[partitionY]\n        if maxLeftX <= minRightY and maxLeftY <= minRightX:\n            if (x + y) % 2 == 0:\n                return (max(maxLeftX, maxLeftY) + min(minRightX, minRightY)) / 2.0\n            else:\n                return max(maxLeftX, maxLeftY)\n        elif maxLeftX > minRightY:\n            high = partitionX - 1\n        else:\n            low = partitionX + 1",
                            "java": "class Solution {\n    public double findMedianSortedArrays(int[] nums1, int[] nums2) {\n        if (nums1.length > nums2.length) return findMedianSortedArrays(nums2, nums1);\n        int x = nums1.length, y = nums2.length;\n        int low = 0, high = x;\n        while (low <= high) {\n            int partitionX = (low + high) / 2;\n            int partitionY = (x + y + 1) / 2 - partitionX;\n            int maxLeftX = (partitionX == 0) ? Integer.MIN_VALUE : nums1[partitionX - 1];\n            int minRightX = (partitionX == x) ? Integer.MAX_VALUE : nums1[partitionX];\n            int maxLeftY = (partitionY == 0) ? Integer.MIN_VALUE : nums2[partitionY - 1];\n            int minRightY = (partitionY == y) ? Integer.MAX_VALUE : nums2[partitionY];\n            if (maxLeftX <= minRightY && maxLeftY <= minRightX) {\n                if ((x + y) % 2 == 0) {\n                    return ((double)Math.max(maxLeftX, maxLeftY) + Math.min(minRightX, minRightY)) / 2.0;\n                } else {\n                    return (double)Math.max(maxLeftX, maxLeftY);\n                }\n            } else if (maxLeftX > minRightY) {\n                high = partitionX - 1;\n            } else {\n                low = partitionX + 1;\n            }\n        }\n        return 0.0;\n    }\n}",
                            "cpp": "double findMedianSortedArrays(vector<int>& nums1, vector<int>& nums2) {\n    if (nums1.size() > nums2.size()) return findMedianSortedArrays(nums2, nums1);\n    int x = nums1.size(), y = nums2.size();\n    int low = 0, high = x;\n    while (low <= high) {\n        int partitionX = (low + high) / 2;\n        int partitionY = (x + y + 1) / 2 - partitionX;\n        int maxLeftX = (partitionX == 0) ? INT_MIN : nums1[partitionX - 1];\n        int minRightX = (partitionX == x) ? INT_MAX : nums1[partitionX];\n        int maxLeftY = (partitionY == 0) ? INT_MIN : nums2[partitionY - 1];\n        int minRightY = (partitionY == y) ? INT_MAX : nums2[partitionY];\n        if (maxLeftX <= minRightY && maxLeftY <= minRightX) {\n            if ((x + y) % 2 == 0) {\n                return (max(maxLeftX, maxLeftY) + min(minRightX, minRightY)) / 2.0;\n            } else {\n                return max(maxLeftX, maxLeftY);\n            }\n        } else if (maxLeftX > minRightY) {\n            high = partitionX - 1;\n        } else {\n            low = partitionX + 1;\n        }\n    }\n    return 0.0;\n}"
                        }
                    },
                    {
                        "title": "Longest Substring Without Repeating Characters",
                        "difficulty": "Medium",
                        "tags": ["Hash Table", "String", "Sliding Window"],
                        "frequency": "High",
                        "question": "Given a string s, find the length of the longest substring without repeating characters.",
                        "answer": "Using the sliding window technique, we maintain a window representing the current non-repeating substring. We use a hash map to store the index of characters and update the left pointer when a duplicate is found.",
                        "solutions": {
                            "python": "def lengthOfLongestSubstring(s):\n    char_map = {}\n    max_len = start = 0\n    for idx, char in enumerate(s):\n        if char in char_map and char_map[char] >= start:\n            start = char_map[char] + 1\n        char_map[char] = idx\n        max_len = max(max_len, idx - start + 1)\n    return max_len",
                            "java": "public int lengthOfLongestSubstring(String s) {\n    Map<Character, Integer> map = new HashMap<>();\n    int maxLen = 0, start = 0;\n    for (int idx = 0; idx < s.length(); idx++) {\n        char c = s.charAt(idx);\n        if (map.containsKey(c) && map.get(c) >= start) {\n            start = map.get(c) + 1;\n        }\n        map.put(c, idx);\n        maxLen = Math.max(maxLen, idx - start + 1);\n    }\n    return maxLen;\n}",
                            "cpp": "int lengthOfLongestSubstring(string s) {\n    unordered_map<char, int> map;\n    int maxLen = 0, start = 0;\n    for (int idx = 0; idx < s.length(); idx++) {\n        if (map.count(s[idx]) && map[s[idx]] >= start) {\n            start = map[s[idx]] + 1;\n        }\n        map[s[idx]] = idx;\n        maxLen = max(maxLen, idx - start + 1)\n    }\n    return maxLen;\n}"
                        }
                    }
                ]
            },
            {
                "title": "System Design",
                "questions": [
                    {
                        "title": "Design a Distributed File System (like Google File System)",
                        "difficulty": "Hard",
                        "tags": ["System Design", "Distributed Systems", "Storage"],
                        "frequency": "High",
                        "question": "How would you design a distributed file system to store petabytes of data reliably with high-throughput reads and writes across thousands of server nodes?",
                        "answer": "Explain the architecture of a single Master node controlling metadata, and multiple Chunkservers storing actual 64MB file chunks. Address replication, failure handling, chunk size justification, and master bottlenecks using metadata caching.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Tell me about a time you had a technical disagreement with a peer",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Googliness", "Collaboration"],
                        "frequency": "Medium",
                        "question": "Describe a scenario where you disagreed on a design choice, and how you reached a resolution.",
                        "answer": "Focus on using objective metrics (e.g. performance benchmarks, maintenance overhead) instead of personal opinions. Highlight active listening, compromise, alignment on goals, and disagree-and-commit principles.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "microsoft": {
        "name": "Microsoft",
        "color": "#F25022",
        "description": "Microsoft interviews focus on robust data structure applications, operating system fundamentals, and customer-obsessed engineering principles.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Reverse Nodes in k-Group",
                        "difficulty": "Hard",
                        "tags": ["Linked List", "Recursion"],
                        "frequency": "High",
                        "question": "Given the head of a linked list, reverse the nodes of the list k at a time and return the modified list.",
                        "answer": "Iterate to find if there are at least k nodes left. If yes, reverse those k nodes and recursively link the remainder. Otherwise, return the current head as is.",
                        "solutions": {
                            "python": "def reverseKGroup(head, k):\n    curr = head\n    count = 0\n    while curr and count < k:\n        curr = curr.next\n        count += 1\n    if count == k:\n        curr = reverseKGroup(curr, k)\n        while count > 0:\n            tmp = head.next\n            head.next = curr\n            curr = head\n            head = tmp\n            count -= 1\n        head = curr\n    return head",
                            "java": "public ListNode reverseKGroup(ListNode head, int k) {\n    ListNode curr = head;\n    int count = 0;\n    while (curr != null && count < k) {\n        curr = curr.next;\n        count++;\n    }\n    if (count == k) {\n        curr = reverseKGroup(curr, k);\n        while (count-- > 0) {\n            ListNode tmp = head.next;\n            head.next = curr;\n            curr = head;\n            head = tmp;\n        }\n        head = curr;\n    }\n    return head;\n}",
                            "cpp": "ListNode* reverseKGroup(ListNode* head, int k) {\n    ListNode* curr = head;\n    int count = 0;\n    while (curr && count < k) {\n        curr = curr->next;\n        count++;\n    }\n    if (count == k) {\n        curr = reverseKGroup(curr, k);\n        while (count-- > 0) {\n            ListNode* tmp = head->next;\n            head->next = curr;\n            curr = head;\n            head = tmp;\n        }\n        head = curr;\n    }\n    return head;\n}"
                        }
                    }
                ]
            },
            {
                "title": "System Design",
                "questions": [
                    {
                        "title": "Design Google Docs (Real-time Collaborative Editor)",
                        "difficulty": "Hard",
                        "tags": ["System Design", "Operational Transformation", "WebSockets"],
                        "frequency": "High",
                        "question": "How would you design a real-time collaborative document editing workspace supporting concurrent editing with conflict resolution?",
                        "answer": "Describe Operational Transformation (OT) or Conflict-Free Replicated Data Types (CRDT) to handle sync. Structure layout with WebSocket connections to a pub/sub layer, caching updates in Redis, and periodically saving document states to relational databases.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "How did you manage a scenario with an extremely tight, near-impossible deadline?",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Time Management", "Prioritization"],
                        "frequency": "High",
                        "question": "Describe a project deadline challenge, how you prioritized deliverables, and the final outcome.",
                        "answer": "Employ the STAR method. Describe how you cut secondary scopes, coordinated aggressively with stakeholders, maintained transparency, and leveraged agile iterations to meet standard milestones.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "amazon": {
        "name": "Amazon",
        "color": "#FF9900",
        "description": "Amazon candidates must demonstrate deep mastery of the 16 Leadership Principles alongside strong algorithmic fundamentals.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Merge k Sorted Lists",
                        "difficulty": "Hard",
                        "tags": ["Linked List", "Divide & Conquer", "Heap"],
                        "frequency": "High",
                        "question": "You are given an array of k linked-lists lists, each linked-list is sorted in ascending order. Merge all the linked-lists into one sorted linked-list and return it.",
                        "answer": "Using a Min-Heap (priority queue), push the head of each non-empty list. Repeatedly pop the smallest node, append it to the merged list, and push its next node.",
                        "solutions": {
                            "python": "import heapq\n\ndef mergeKLists(lists):\n    min_heap = []\n    for idx, l in enumerate(lists):\n        if l:\n            heapq.heappush(min_heap, (l.val, idx, l))\n    \n    dummy = ListNode(0)\n    curr = dummy\n    while min_heap:\n        val, idx, node = heapq.heappop(min_heap)\n        curr.next = node\n        curr = curr.next\n        if node.next:\n            heapq.heappush(min_heap, (node.next.val, idx, node.next))\n    return dummy.next",
                            "java": "public ListNode mergeKLists(ListNode[] lists) {\n    PriorityQueue<ListNode> pq = new PriorityQueue<>((a, b) -> a.val - b.val);\n    for (ListNode l : lists) {\n        if (l != null) pq.add(l);\n    }\n    ListNode dummy = new ListNode(0);\n    ListNode curr = dummy;\n    while (!pq.isEmpty()) {\n        ListNode node = pq.poll();\n        curr.next = node;\n        curr = curr.next;\n        if (node.next != null) pq.add(node.next);\n    }\n    return dummy.next;\n}",
                            "cpp": "struct Compare {\n    bool operator()(ListNode* a, ListNode* b) { return a->val > b->val; }\n};\nListNode* mergeKLists(vector<ListNode*>& lists) {\n    priority_queue<ListNode*, vector<ListNode*>, Compare> pq;\n    for (auto l : lists) if (l) pq.push(l);\n    ListNode* dummy = new ListNode(0);\n    ListNode* curr = dummy;\n    while (!pq.empty()) {\n        ListNode* node = pq.top(); pq.pop();\n        curr->next = node;\n        curr = curr->next;\n        if (node->next) pq.push(node->next);\n    }\n    return dummy->next;\n}"
                        }
                    }
                ]
            },
            {
                "title": "System Design",
                "questions": [
                    {
                        "title": "Design an E-commerce Cart System (Amazon Cart)",
                        "difficulty": "Medium",
                        "tags": ["System Design", "Database Cache", "Session Store"],
                        "frequency": "High",
                        "question": "How would you design a highly available shopping cart system that preserves items across devices and maintains performance during flash sales?",
                        "answer": "Describe a decoupled shopping service: Session caches in Redis for active carts, persistent storage using NoSQL databases (e.g. DynamoDB) for saved carts, write-back sync procedures, and scaling techniques using load balancers and queue throttling.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Describe a time when you put the customer's interest first (Customer Obsession)",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Customer Obsession", "Leadership Principles"],
                        "frequency": "High",
                        "question": "Discuss a scenario where you went out of your way to solve an issue for a customer, even if it meant delaying normal project schedules.",
                        "answer": "Structure your answer around STAR. Describe how you diagnosed a bug impacting users, organized support channels, adjusted priorities, resolved the blocker, and implemented features to prevent recurrence.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "meta": {
        "name": "Meta",
        "color": "#0668E1",
        "description": "Meta interviews focus heavily on quick coding, scale, caching strategies, and graph theory.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Subarray Sum Equals K",
                        "difficulty": "Medium",
                        "tags": ["Array", "Hash Table", "Prefix Sum"],
                        "frequency": "High",
                        "question": "Given an array of integers nums and an integer k, return the total number of subarrays whose sum equals to k.",
                        "answer": "Maintain a running prefix sum and map its occurrences. For each step, if prefix_sum - k exists in the map, add its frequency count to the result.",
                        "solutions": {
                            "python": "def subarraySum(nums, k):\n    count = 0\n    pref_sum = 0\n    sums_dict = {0: 1}\n    for num in nums:\n        pref_sum += num\n        if pref_sum - k in sums_dict:\n            count += sums_dict[pref_sum - k]\n        sums_dict[pref_sum] = sums_dict.get(pref_sum, 0) + 1\n    return count",
                            "java": "public int subarraySum(int[] nums, int k) {\n    int count = 0, prefSum = 0;\n    Map<Integer, Integer> map = new HashMap<>();\n    map.put(0, 1);\n    for (int num : nums) {\n        prefSum += num;\n        if (map.containsKey(prefSum - k)) {\n            count += map.get(prefSum - k);\n        }\n        map.put(prefSum, map.getOrDefault(prefSum, 0) + 1);\n    }\n    return count;\n}",
                            "cpp": "int subarraySum(vector<int>& nums, int k) {\n    int count = 0, prefSum = 0;\n    unordered_map<int, int> map;\n    map[0] = 1;\n    for (int num : nums) {\n        prefSum += num;\n        if (map.count(prefSum - k)) {\n            count += map[prefSum - k];\n        }\n        map[prefSum]++;\n    }\n    return count;\n}"
                        }
                    }
                ]
            },
            {
                "title": "System Design",
                "questions": [
                    {
                        "title": "Design Facebook News Feed",
                        "difficulty": "Hard",
                        "tags": ["System Design", "Fanout", "Feed Optimization"],
                        "frequency": "High",
                        "question": "How would you design the news feed generation and distribution system for a platform with millions of active users?",
                        "answer": "Discuss feed generation models: Push (Fanout-on-write) for low-volume creators, Pull (Fanout-on-read) for high-following celebrities, hybrid layouts, cache servers (Redis clusters) for feeds, CDN storage for media, and load balancers.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Tell me about a time you had to deal with a conflict in your project team",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Conflict Resolution", "Collaboration"],
                        "frequency": "High",
                        "question": "Describe a personal mismatch or technical disagreement in a group project and how you resolved it.",
                        "answer": "Discuss active listening, holding private alignments to understand opposing priorities, mapping compromise outcomes, using objective trade-off lists, and committing fully to the group decision.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "netflix": {
        "name": "Netflix",
        "color": "#E50914",
        "description": "Netflix values high-performance distributed streaming designs, scalability, and independence aligned with their famous culture memo.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "LRU Cache",
                        "difficulty": "Medium",
                        "tags": ["Hash Table", "Linked List", "Design"],
                        "frequency": "High",
                        "question": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.",
                        "answer": "Implement the cache using a combination of a Doubly Linked List (to maintain insertion/access order) and a Hash Map (for O(1) lookups). Update order on every read/write.",
                        "solutions": {
                            "python": "class Node:\n    def __init__(self, key, val):\n        self.key, self.val = key, val\n        self.prev = self.next = None\n\nclass LRUCache:\n    def __init__(self, capacity: int):\n        self.cap = capacity\n        self.cache = {}\n        self.left, self.right = Node(0, 0), Node(0, 0)\n        self.left.next, self.right.prev = self.right, self.left\n\n    def remove(self, node):\n        prev, nxt = node.prev, node.next\n        prev.next, nxt.prev = nxt, prev\n\n    def insert(self, node):\n        prev, nxt = self.right.prev, self.right\n        prev.next = nxt.prev = node\n        node.prev, node.next = prev, nxt\n\n    def get(self, key: int) -> int:\n        if key in self.cache:\n            self.remove(self.cache[key])\n            self.insert(self.cache[key])\n            return self.cache[key].val\n        return -1\n\n    def put(self, key: int, value: int) -> None:\n        if key in self.cache:\n            self.remove(self.cache[key])\n        self.cache[key] = Node(key, value)\n        self.insert(self.cache[key])\n        if len(self.cache) > self.cap:\n            lru = self.left.next\n            self.remove(lru)\n            del self.cache[lru.key]",
                            "java": "class LRUCache {\n    class Node {\n        int key, value;\n        Node prev, next;\n        Node(int k, int v) { key = k; value = v; }\n    }\n    private int capacity;\n    private Map<Integer, Node> map = new HashMap<>();\n    private Node head = new Node(0, 0), tail = new Node(0, 0);\n\n    public LRUCache(int cap) {\n        capacity = cap;\n        head.next = tail;\n        tail.prev = head;\n    }\n    private void remove(Node n) {\n        n.prev.next = n.next;\n        n.next.prev = n.prev;\n    }\n    private void insert(Node n) {\n        n.next = head.next;\n        n.next.prev = n; \n        head.next = n;\n        n.prev = head;\n    }\n    public int get(int key) {\n        if (map.containsKey(key)) {\n            Node n = map.get(key);\n            remove(n); insert(n);\n            return n.value;\n        }\n        return -1;\n    }\n    public void put(int key, int value) {\n        if (map.containsKey(key)) remove(map.get(key));\n        Node n = new Node(key, value);\n        insert(n); map.put(key, n);\n        if (map.size() > capacity) {\n            map.remove(tail.prev.key);\n            remove(tail.prev);\n        }\n    }\n}",
                            "cpp": "class LRUCache {\n    struct Node {\n        int key, val;\n        Node *prev, *next;\n        Node(int k, int v): key(k), val(v), prev(nullptr), next(nullptr) {}\n    };\n    int cap;\n    unordered_map<int, Node*> map;\n    Node* head = new Node(0, 0);\n    Node* tail = new Node(0, 0);\n    void remove(Node* n) {\n        n->prev->next = n->next;\n        n->next->prev = n->prev;\n    }\n    void insert(Node* n) {\n        n->next = head->next;\n        n->next->prev = n;\n        head->next = n;\n        n->prev = head;\n    }\npublic:\n    LRUCache(int capacity): cap(capacity) {\n        head->next = tail; tail->prev = head;\n    }\n    int get(int key) {\n        if (map.count(key)) {\n            remove(map[key]); insert(map[key]);\n            return map[key]->val;\n        }\n        return -1;\n    }\n    void put(int key, int value) {\n        if (map.count(key)) remove(map[key]);\n        Node* n = new Node(key, value);\n        insert(n); map[key] = n;\n        if (map.size() > cap) {\n            map.erase(tail->prev->key);\n            remove(tail->prev);\n        }\n    }\n};"
                        }
                    }
                ]
            },
            {
                "title": "System Design",
                "questions": [
                    {
                        "title": "Design a Video Streaming Pipeline",
                        "difficulty": "Hard",
                        "tags": ["System Design", "CDN", "Transcoding"],
                        "frequency": "High",
                        "question": "How would you ingest, transcode, and deliver high-quality video content globally with low latency?",
                        "answer": "Describe high-level architecture: Video files uploaded to S3 -> Ingest triggers chunked Transcoding service -> Dynamic manifest file generation (HLS/DASH) -> Storage in Edge Caches / CDNs. Highlight cache strategies and adaptive bitrate streaming (ABR).",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "How do you align yourself with the Netflix Culture of 'Freedom & Responsibility'?",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Culture Fit", "Netflix Pillars"],
                        "frequency": "High",
                        "question": "Discuss how you balance high autonomy with strict technical accountability in past engineering roles.",
                        "answer": "Focus on self-motivation, taking ownership of production environments, keeping codebases thoroughly documented, building clear monitoring tools, and collaborating actively without heavy oversight.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "tcs": {
        "name": "TCS",
        "color": "#1A5A96",
        "description": "TCS exams assess core aptitude, fundamental data structures, C/Java programming basics, and general reasoning questions.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Prime Factorization",
                        "difficulty": "Easy",
                        "tags": ["Fundamentals", "Math"],
                        "frequency": "High",
                        "question": "Write a program to display all prime factors of a given integer N.",
                        "answer": "Iterate from 2 to sqrt(N). While divisor divides N, print divisor and divide N by it. If remaining N > 2, print N.",
                        "solutions": {
                            "python": "def primeFactors(n):\n    while n % 2 == 0:\n        print(2)\n        n //= 2\n    for i in range(3, int(n**0.5)+1, 2):\n        while n % i == 0:\n            print(i)\n            n //= i\n    if n > 2:\n        print(n)",
                            "java": "public void primeFactors(int n) {\n    while (n % 2 == 0) {\n        System.out.println(2);\n        n /= 2;\n    }\n    for (int i = 3; i * i <= n; i += 2) {\n        while (n % i == 0) {\n            System.out.println(i);\n            n /= i;\n        }\n    }\n    if (n > 2) System.out.println(n);\n}",
                            "cpp": "void primeFactors(int n) {\n    while (n % 2 == 0) {\n        cout << 2 << endl;\n        n /= 2;\n    }\n    for (int i = 3; i * i <= n; i += 2) {\n        while (n % i == 0) {\n            cout << i << endl;\n            n /= i;\n        }\n    }\n    if (n > 2) cout << n << endl;\n}"
                        }
                    },
                    {
                        "title": "Reverse a String",
                        "difficulty": "Easy",
                        "tags": ["String", "Two Pointers"],
                        "frequency": "High",
                        "question": "Write a program to reverse a given input string without using built-in reverse functions.",
                        "answer": "Use two pointers, one at the beginning and one at the end of the string, swap characters, and move them towards each other until they meet.",
                        "solutions": {
                            "python": "def reverseString(s):\n    chars = list(s)\n    left, right = 0, len(chars) - 1\n    while left < right:\n        chars[left], chars[right] = chars[right], chars[left]\n        left += 1\n        right -= 1\n    return ''.join(chars)",
                            "java": "public String reverseString(String s) {\n    char[] chars = s.toCharArray();\n    int left = 0, right = chars.length - 1;\n    while (left < right) {\n        char tmp = chars[left];\n        chars[left] = chars[right];\n        chars[right] = tmp;\n        left++; right--;\n    }\n    return new String(chars);\n}",
                            "cpp": "string reverseString(string s) {\n    int left = 0, right = s.length() - 1;\n    while (left < right) {\n        swap(s[left], s[right]);\n        left++; right--;\n    }\n    return s;\n}"
                        }
                    }
                ]
            },
            {
                "title": "Aptitude & General",
                "questions": [
                    {
                        "title": "Work and Time Aptitude Problem",
                        "difficulty": "Easy",
                        "tags": ["Aptitude", "Math"],
                        "frequency": "High",
                        "question": "If A can complete a work in 10 days and B can complete it in 15 days, in how many days can they complete the work if they work together?",
                        "answer": "Find individual rates. A's rate is 1/10 per day, B's rate is 1/15 per day. Combined rate = 1/10 + 1/15 = 5/30 = 1/6 per day. Thus, together they need 6 days.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Why do you want to join TCS?",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Culture Fit"],
                        "frequency": "High",
                        "question": "Explain your motivation for starting your career at a global IT consulting leader like Tata Consultancy Services.",
                        "answer": "Emphasize TCS's robust training frameworks (e.g. Initial Learning Program - ILP), global project exposure, diversity of domains (Finance, Retail, Healthcare), and stability as a top employer.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "infosys": {
        "name": "Infosys",
        "color": "#007CC3",
        "description": "Infosys assessment questions target algorithmic coding, logical reasoning, and basic Java/Python programming questions.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Count Special Characters",
                        "difficulty": "Easy",
                        "tags": ["String", "Logic"],
                        "frequency": "High",
                        "question": "Given a string, find the number of special characters present in it (excluding alphanumeric characters and spaces).",
                        "answer": "Iterate through the string, check if each character is alphanumeric or space, and if not, increment the counter.",
                        "solutions": {
                            "python": "def countSpecial(s):\n    return sum(1 for c in s if not c.isalnum() and c != ' ')",
                            "java": "public int countSpecial(String s) {\n    int count = 0;\n    for(char c : s.toCharArray()) {\n        if(!Character.isLetterOrDigit(c) && c != ' ') count++;\n    }\n    return count;\n}",
                            "cpp": "int countSpecial(string s) {\n    int count = 0;\n    for(char c : s) {\n        if(!isalnum(c) && c != ' ') count++;\n    }\n    return count;\n}"
                        }
                    }
                ]
            },
            {
                "title": "Aptitude & General",
                "questions": [
                    {
                        "title": "Permutations and Combinations",
                        "difficulty": "Easy",
                        "tags": ["Math", "Aptitude"],
                        "frequency": "Medium",
                        "question": "In how many different ways can the letters of the word 'LEADING' be arranged in such a way that the vowels always come together?",
                        "answer": "The word 'LEADING' has 7 letters, including vowels E, A, I (3 vowels) and consonants L, D, N, G (4 consonants). Since vowels must be together, treat (E, A, I) as 1 unit. Total units to arrange = 4 consonants + 1 unit = 5 units. Ways to arrange 5 units = 5! = 120. Ways to arrange vowels inside their unit = 3! = 6. Total arrangements = 120 * 6 = 720.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Describe a project challenge you resolved",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Problem Solving"],
                        "frequency": "Medium",
                        "question": "Discuss a technical or team challenge you faced in a academic project and how you resolved it.",
                        "answer": "Focus on the structured problem analysis, research of alternatives, collaboration with team members, implementation of the fix, and validating the final system state.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "wipro": {
        "name": "Wipro",
        "color": "#000000",
        "description": "Wipro Elite National Talent Hunt (NLTH) questions test foundational coding, object-oriented concepts, and basic data structures.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Check if Anagram",
                        "difficulty": "Easy",
                        "tags": ["String", "Sorting"],
                        "frequency": "High",
                        "question": "Write a function to check whether two given strings are anagrams of each other.",
                        "answer": "Sort both strings and check if they are identical. Alternatively, use a frequency array or hash map to count character frequencies.",
                        "solutions": {
                            "python": "def isAnagram(s1, s2):\n    return sorted(s1) == sorted(s2)",
                            "java": "public boolean isAnagram(String s1, String s2) {\n    char[] c1 = s1.toCharArray();\n    char[] c2 = s2.toCharArray();\n    java.util.Arrays.sort(c1);\n    java.util.Arrays.sort(c2);\n    return java.util.Arrays.equals(c1, c2);\n}",
                            "cpp": "bool isAnagram(string s1, string s2) {\n    sort(s1.begin(), s1.end());\n    sort(s2.begin(), s2.end());\n    return s1 == s2;\n}"
                        }
                    }
                ]
            },
            {
                "title": "Aptitude & General",
                "questions": [
                    {
                        "title": "LCM and HCF Problem",
                        "difficulty": "Easy",
                        "tags": ["Math", "Aptitude"],
                        "frequency": "High",
                        "question": "The HCF of two numbers is 11 and their LCM is 7700. If one of the numbers is 275, find the other.",
                        "answer": "Using the relation: Product of two numbers = LCM * HCF. Thus, 275 * X = 7700 * 11. X = (7700 * 11) / 275 = 84700 / 275 = 308.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Why Wipro Elite?",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Culture Fit"],
                        "frequency": "Medium",
                        "question": "How do you align with Wipro's values of integrity, respect, and stewardship?",
                        "answer": "Describe your focus on ethical engineering, active learning, professional respect, and contributing to sustainability and team growth.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "accenture": {
        "name": "Accenture",
        "color": "#A100FF",
        "description": "Accenture assessments focus heavily on coding, logical reasoning, pseudo-code execution, and critical thinking.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Find Binary Operations",
                        "difficulty": "Medium",
                        "tags": ["Bit Manipulation", "Logic"],
                        "frequency": "High",
                        "question": "Implement a function that performs basic binary operations (AND, OR, XOR) on an input string containing binary numbers and operation characters (A, B, C representing AND, OR, XOR) and returns the output.",
                        "answer": "Iterate through the string step by step, evaluating the expression from left to right using the current operation character on the adjacent binary digits.",
                        "solutions": {
                            "python": "def evalBinaryStr(s):\n    if not s: return -1\n    res = int(s[0])\n    i = 1\n    while i < len(s):\n        op = s[i]\n        val = int(s[i+1])\n        if op == 'A': res &= val\n        elif op == 'B': res |= val\n        elif op == 'C': res ^= val\n        i += 2\n    return res",
                            "java": "public int evalBinaryStr(String s) {\n    if (s == null || s.length() == 0) return -1;\n    int res = Character.getNumericValue(s.charAt(0));\n    for (int i = 1; i < s.length(); i += 2) {\n        char op = s.charAt(i);\n        int val = Character.getNumericValue(s.charAt(i+1));\n        if (op == 'A') res &= val;\n        else if (op == 'B') res |= val;\n        else if (op == 'C') res ^= val;\n    }\n    return res;\n}",
                            "cpp": "int evalBinaryStr(string s) {\n    if (s.empty()) return -1;\n    int res = s[0] - '0';\n    for (size_t i = 1; i < s.length(); i += 2) {\n        char op = s[i];\n        int val = s[i+1] - '0';\n        if (op == 'A') res &= val;\n        else if (op == 'B') res |= val;\n        else if (op == 'C') res ^= val;\n    }\n    return res;\n}"
                        }
                    }
                ]
            },
            {
                "title": "Aptitude & General",
                "questions": [
                    {
                        "title": "Profit and Loss Problem",
                        "difficulty": "Easy",
                        "tags": ["Math", "Aptitude"],
                        "frequency": "High",
                        "question": "A shopkeeper sells an article at a loss of 12.5%. If he had sold it for Rs. 30 more, he would have gained 2.5%. Find the cost price of the article.",
                        "answer": "Let Cost Price be CP. Initial selling price = CP - 0.125 * CP = 0.875 * CP. New selling price = CP + 0.025 * CP = 1.025 * CP. Difference = 1.025 * CP - 0.875 * CP = 0.15 * CP. Given difference = Rs. 30. Thus, 0.15 * CP = 30 => CP = 30 / 0.15 = 200.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Collaboration under pressure",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Teamwork"],
                        "frequency": "High",
                        "question": "Give an example of a time you worked with a cross-functional team under a tight schedule.",
                        "answer": "Describe division of labor, regular updates, clear interface definition, mutual support, and focusing on MVP execution to hit the project deadline successfully.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "cognizant": {
        "name": "Cognizant",
        "color": "#000048",
        "description": "Cognizant GenC and GenC Next assessments evaluate relational database SQL, data structure code, and coding logic.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "SQL Join and Aggregate",
                        "difficulty": "Medium",
                        "tags": ["SQL", "Database"],
                        "frequency": "High",
                        "question": "Write an SQL query to retrieve employee names and their total sales values from two tables: employees and sales, grouping by employee name.",
                        "answer": "Use an INNER JOIN on employee_id, and use SUM(sales.amount) grouped by employees.name.",
                        "solutions": {
                            "sql": "SELECT e.name, SUM(s.amount) AS total_sales\nFROM employees e\nINNER JOIN sales s ON e.employee_id = s.employee_id\nGROUP BY e.name;"
                        }
                    }
                ]
            },
            {
                "title": "Aptitude & General",
                "questions": [
                    {
                        "title": "Pipes and Cisterns",
                        "difficulty": "Easy",
                        "tags": ["Math", "Aptitude"],
                        "frequency": "Medium",
                        "question": "Three pipes A, B and C can fill a tank in 6 hours. After working at it together for 2 hours, C is closed and A and B can fill it in 7 hours. How many hours will C alone take to fill the tank?",
                        "answer": "A, B and C's 1 hour work = 1/6. Work done in 2 hours = 2/6 = 1/3. Remaining work = 1 - 1/3 = 2/3. A and B do 2/3 work in 7 hours. So, A and B do 1 work in 21/2 hours. A and B's 1 hour work = 2/21. C's 1 hour work = (A+B+C)'s 1 hour work - (A+B)'s 1 hour work = 1/6 - 2/21 = (7 - 4) / 42 = 3/42 = 1/14. Thus, C alone takes 14 hours.",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Why Cognizant?",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Culture Fit"],
                        "frequency": "Medium",
                        "question": "Explain your choice to start your professional career at Cognizant.",
                        "answer": "Mention the robust digital engineering practices, training programs, opportunity to work with international clients, and commitment to innovation.",
                        "solutions": {}
                    }
                ]
            }
        ]
    },
    "capgemini": {
        "name": "Capgemini",
        "color": "#0066B3",
        "description": "Capgemini interview tracks test data structures, pseudo-coding logic, game-based aptitude, and cloud architecture basics.",
        "categories": [
            {
                "title": "Coding & Data Structures",
                "questions": [
                    {
                        "title": "Find Second Largest Element",
                        "difficulty": "Easy",
                        "tags": ["Array", "Logic"],
                        "frequency": "High",
                        "question": "Given an array of integers, find the second largest element. Handle duplicates.",
                        "answer": "Traverse the array once, keeping track of the largest and second largest elements. Initialize both to negative infinity.",
                        "solutions": {
                            "python": "def secondLargest(arr):\n    first = second = float('-inf')\n    for n in arr:\n        if n > first:\n            second = first\n            first = n\n        elif n > second and n != first:\n            second = n\n    return second if second != float('-inf') else -1",
                            "java": "public int secondLargest(int[] arr) {\n    int first = Integer.MIN_VALUE, second = Integer.MIN_VALUE;\n    for(int n : arr) {\n        if(n > first) {\n            second = first;\n            first = n;\n        } else if(n > second && n != first) {\n            second = n;\n        }\n    }\n    return second == Integer.MIN_VALUE ? -1 : second;\n}",
                            "cpp": "int secondLargest(vector<int>& arr) {\n    int first = INT_MIN, second = INT_MIN;\n    for(int n : arr) {\n        if(n > first) {\n            second = first;\n            first = n;\n        } else if(n > second && n != first) {\n            second = n;\n        }\n    }\n    return second == INT_MIN ? -1 : second;\n}"
                        }
                    }
                ]
            },
            {
                "title": "Aptitude & General",
                "questions": [
                    {
                        "title": "Simple Interest and Compound Interest",
                        "difficulty": "Easy",
                        "tags": ["Math", "Aptitude"],
                        "frequency": "High",
                        "question": "The difference between simple interest and compound interest on Rs. 12000 for 2 years at 10% per annum, compounded annually is how much?",
                        "answer": "Simple Interest (SI) = (12000 * 10 * 2) / 100 = 2400. Compound Interest (CI) = 12000 * (1 + 10/100)^2 - 12000 = 12000 * 1.21 - 12000 = 14520 - 12000 = 2520. Difference = 2520 - 2400 = 120. (Alternatively, Difference = P(R/100)^2 = 12000 * (10/100)^2 = 12000 * 1/100 = 120).",
                        "solutions": {}
                    }
                ]
            },
            {
                "title": "Behavioral",
                "questions": [
                    {
                        "title": "Explain your adaptability skills",
                        "difficulty": "Easy",
                        "tags": ["Behavioral", "Adaptability"],
                        "frequency": "Medium",
                        "question": "Tell us about a time you had to adapt quickly to a major shift in tech stack or project rules.",
                        "answer": "Describe your learning strategy, leveraging documentation, searching for code examples, doing sandbox tests, and reaching out to team leads/peers to quickly gain productivity.",
                        "solutions": {}
                    }
                ]
            }
        ]
    }
}

if __name__ == '__main__':
    # Write to questions.json
    target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'questions.json')
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(COMPANY_QUESTIONS, f, indent=4)
    print(f"Successfully generated {target_path} with {len(COMPANY_QUESTIONS)} companies.")
