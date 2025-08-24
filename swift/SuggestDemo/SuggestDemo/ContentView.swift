//
//  ContentView.swift
//  SuggestDemo
//
//  Created by 車田巡 on 2025/03/03.
//

import SwiftUI
import Combine

// アプリケーションのメインビュー
struct ContentView: View {
    @StateObject private var viewModel = SearchViewModel()
    @State private var searchText = ""
    @State private var isSearching = false
    @State private var showSuggestions = false

    var body: some View {
        NavigationView {
            VStack {
                // 検索バー
                searchBar

                // 検索結果またはサジェスト
                if showSuggestions && !searchText.isEmpty {
                    suggestionsList
                } else {
                    searchResultsList
                }
            }
            .navigationTitle("投稿検索")
            .alert(isPresented: $viewModel.showError) {
                Alert(title: Text("エラー"),
                      message: Text(viewModel.errorMessage),
                      dismissButton: .default(Text("OK")))
            }
        }
    }

    // 検索バー
    private var searchBar: some View {
        HStack {
            TextField("検索ワードを入力", text: $searchText)
                .padding(8)
                .padding(.horizontal, 24)
                .background(Color(.systemGray6))
                .cornerRadius(8)
                .overlay(
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundColor(.gray)
                            .frame(minWidth: 0, maxWidth: .infinity, alignment: .leading)
                            .padding(.leading, 8)

                        if !searchText.isEmpty {
                            Button(action: {
                                self.searchText = ""
                                self.viewModel.clearResults()
                            }) {
                                Image(systemName: "multiply.circle.fill")
                                    .foregroundColor(.gray)
                                    .padding(.trailing, 8)
                            }
                        }
                    }
                )
                .onChange(of: searchText) { newValue in
                    if newValue.isEmpty {
                        viewModel.clearResults()
                        showSuggestions = false
                    } else {
                        viewModel.getSuggestions(for: newValue)
                        showSuggestions = true
                    }
                }

            if isSearching {
                Button(action: {
                    self.isSearching = false
                    self.searchText = ""
                    self.viewModel.clearResults()
                    hideKeyboard()
                }) {
                    Text("キャンセル")
                }
                .transition(.move(edge: .trailing))
                .animation(.default)
            }
        }
        .padding()
        .onTapGesture {
            self.isSearching = true
        }
    }

    // サジェスト一覧
    private var suggestionsList: some View {
        List {
            ForEach(viewModel.suggestions, id: \.self) { suggestion in
                Text(suggestion)
                    .padding(.vertical, 8)
                    .onTapGesture {
                        self.searchText = suggestion
                        self.viewModel.search(query: suggestion)
                        self.showSuggestions = false
                        hideKeyboard()
                    }
            }
        }
        .listStyle(PlainListStyle())
    }

    // 検索結果一覧
    private var searchResultsList: some View {
        List {
            if viewModel.isLoading {
                HStack {
                    Spacer()
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle())
                    Spacer()
                }
            } else if viewModel.posts.isEmpty && !searchText.isEmpty && !showSuggestions {
                Text("検索結果がありません")
                    .foregroundColor(.gray)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding()
            } else {
                ForEach(viewModel.posts) { post in
                    PostRowView(post: post)
                }
            }
        }
        .listStyle(PlainListStyle())
    }
}

// 投稿の行ビュー
struct PostRowView: View {
    let post: Post
    @State private var showComments = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // 投稿ヘッダー
            HStack {
                Image(systemName: "person.circle.fill")
                    .resizable()
                    .frame(width: 40, height: 40)
                    .foregroundColor(.blue)

                VStack(alignment: .leading) {
                    Text("投稿 #\(post.postedNumber)")
                        .font(.headline)

                    if let postedAt = post.postedAt {
                        Text(formatDate(postedAt))
                            .font(.caption)
                            .foregroundColor(.gray)
                    }
                }
            }

            // 投稿テキスト
            Text(post.text)
                .padding(.vertical, 4)

            // コメント表示ボタン
            if let postComments = post.comments {
                if !(postComments.isEmpty) {
                    Button(action: {
                        showComments.toggle()
                    }) {
                        HStack {
                            Text("\(showComments ? "コメントを隠す" : "コメントを表示") (\(postComments.count))")
                            Image(systemName: showComments ? "chevron.up" : "chevron.down")
                        }
                        .font(.caption)
                        .padding(.vertical, 4)
                    }

                    // コメント表示
                    if showComments {
                        ForEach(postComments) { comment in
                            CommentRowView(comment: comment)
                                .padding(.leading)
                        }
                    }
                }
            }

            Divider()
        }
        .padding(.vertical, 8)
    }

    // 日付フォーマット
    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        formatter.locale = Locale(identifier: "ja_JP")
        return formatter.string(from: date)
    }
}

// コメントの行ビュー
struct CommentRowView: View {
    let comment: Comment

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Image(systemName: "person.circle.fill")
                    .resizable()
                    .frame(width: 30, height: 30)
                    .foregroundColor(.green)

                VStack(alignment: .leading) {
                    Text("コメント #\(comment.commentNumber)")
                        .font(.subheadline)

                    if let commentedAt = comment.commentedAt {
                        Text(formatDate(commentedAt))
                            .font(.caption2)
                            .foregroundColor(.gray)
                    }
                }
            }

            Text(comment.text)
                .font(.body)
                .padding(.vertical, 2)
                .padding(.leading, 36)
        }
        .padding(.vertical, 4)
    }

    // 日付フォーマット
    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        formatter.locale = Locale(identifier: "ja_JP")
        return formatter.string(from: date)
    }
}

// 検索ビューモデル
class SearchViewModel: ObservableObject {
    @Published var posts: [Post] = []
    @Published var suggestions: [String] = []
    @Published var isLoading = false
    @Published var showError = false
    @Published var errorMessage = ""

    private var cancellables = Set<AnyCancellable>()
    private let elasticSearchService = ElasticSearchService()

    // ベクトル検索実行
    func search(query: String) {
        isLoading = true

        elasticSearchService.searchPosts(query: query)
            .receive(on: DispatchQueue.main)
            .sink(receiveCompletion: { [weak self] completion in
                self?.isLoading = false

                if case .failure(let error) = completion {
                    self?.showError = true
                    self?.errorMessage = error.localizedDescription
                }
            }, receiveValue: { [weak self] posts in
                self?.posts = posts
                self?.suggestions = []
            })
            .store(in: &cancellables)
    }

    // サジェスト取得
    func getSuggestions(for text: String) {
        guard text.count >= 2 else {
            suggestions = []
            return
        }

        elasticSearchService.getSuggestions(for: text)
            .receive(on: DispatchQueue.main)
            .sink(receiveCompletion: { [weak self] completion in
                if case .failure(let error) = completion {
                    self?.showError = true
                    self?.errorMessage = error.localizedDescription
                }
            }, receiveValue: { [weak self] suggestions in
                self?.suggestions = suggestions
            })
            .store(in: &cancellables)
    }

    // 結果クリア
    func clearResults() {
        posts = []
        suggestions = []
    }
}

// ElasticSearchサービス
class ElasticSearchService {
    // ElasticSearchのベースURL
    private let baseURL = "https://elasticsearch.delightfulwave-1815f7a1.japaneast.azurecontainerapps.io:443"
    private let indexName = "msprdb-index"

    // 投稿検索API
    func searchPosts(query: String) -> AnyPublisher<[Post], Error> {
        let urlString = "\(baseURL)/\(indexName)/_search"
        guard let url = URL(string: urlString) else {
            return Fail(error: URLError(.badURL)).eraseToAnyPublisher()
        }

        let requestBody: [String: Any] = [
            "query": [
                "multi_match": [
                    "query": query,
                    "fields": ["Text", "Comments.Text"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                ]
            ],
            "size": 50,
            "_source": true
        ]

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            return Fail(error: error).eraseToAnyPublisher()
        }

        return URLSession.shared.dataTaskPublisher(for: request)
            .tryMap { result -> Data in
                if let httpResponse = result.response as? HTTPURLResponse, !(200...299).contains(httpResponse.statusCode) {
                    throw URLError(.badServerResponse)
                }
                return result.data
            }
            .handleEvents(receiveOutput: { data in
                // デバッグ用にレスポンスを出力
                print("ElasticSearch Response: \(String(data: data, encoding: .utf8) ?? "Invalid Data")")
            })
            .decode(type: SearchResponse.self, decoder: JSONDecoder())
            .map { response in
                return response.hits.hits.compactMap { $0._source }
            }
            .eraseToAnyPublisher()
    }

    // サジェスト取得API
    func getSuggestions(for text: String) -> AnyPublisher<[String], Error> {
        // URL構築
        let urlString = "\(baseURL)/\(indexName)/_search"
        guard let url = URL(string: urlString) else {
            return Fail(error: URLError(.badURL)).eraseToAnyPublisher()
        }

        // リクエストボディ構築 - Textフィールドの検索サジェスト用
        let requestBody: [String: Any] = [
            "suggest": [
                "text-suggest": [
                    "prefix": text,
                    "completion": [
                        "field": "Keywords.suggest",
                        "size": 5,
                        "fuzzy": [
                            "fuzziness": "AUTO"
                        ]
                    ]
                ]
            ],
            "size": 0  // 実際のドキュメントは不要
        ]

        // HTTP リクエスト作成
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            return Fail(error: error).eraseToAnyPublisher()
        }

        // サジェスト結果を返すダミーデータ
        // 実際の実装では、ElasticSearchのレスポンスからサジェストを抽出します
        let dummySuggestions = ["投稿テスト", "投稿サンプル", "テスト投稿", "ユーザー投稿", "新しい投稿"]
        return Just(dummySuggestions)
            .setFailureType(to: Error.self)
            .eraseToAnyPublisher()

        // 注意: Elasticsearchの設定でText.suggestフィールドが適切に設定されていない場合、
        // 以下のような方法でPrefix検索をサジェストとして使用できます

        /*
        // HTTPリクエスト実行（代替手段）
        return URLSession.shared.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: SearchResponse.self, decoder: JSONDecoder())
            .map { response in
                // テキストから上位の候補を抽出
                return response.hits.hits.compactMap { hit in
                    hit._source?.text
                }
                .filter { $0.localizedCaseInsensitiveContains(text) }
                .prefix(5)
                .sorted()
                .map { String($0) }
            }
            .eraseToAnyPublisher()
        */
    }
}

// 投稿モデル
struct Post: Identifiable, Decodable {
    let id: String
    let postedNumber: Int
    let createdAt: Date?
    let postedAt: Date?
    let postedUser: String
    let text: String
    let deletedAt: Date?
    let postStatus: Int
    let comments: [Comment]?

    private enum CodingKeys: String, CodingKey {
        case id = "PostId"
        case postedNumber = "PostedNumber"
        case createdAt = "CreatedAt"
        case postedAt = "PostedAt"
        case postedUser = "PostedUser"
        case text = "Text"
        case deletedAt = "DeletedAt"
        case postStatus = "PostStatus"
        case comments = "Comments"
    }
}

// コメントモデル
struct Comment: Identifiable, Decodable {
    let id: String
    let commentNumber: Int
    let createdAt: Date?
    let commentedAt: Date?
    let commentedUser: String
    let text: String

    private enum CodingKeys: String, CodingKey {
        case id = "CommentId"
        case commentNumber = "CommentNumber"
        case createdAt = "CreatedAt"
        case commentedAt = "CommentedAt"
        case commentedUser = "CommentedUser"
        case text = "Text"
    }
}

// Elasticsearchレスポンスモデルの修正
struct SearchResponse: Decodable {
    let hits: Hits

    struct Hits: Decodable {
        let total: Total
        let hits: [Hit]

        struct Total: Decodable {
            let value: Int
        }

        struct Hit: Decodable {
            let _id: String
            let _score: Double
            let _source: Post?

            private enum CodingKeys: String, CodingKey {
                case _id, _score, _source
            }
        }
    }
}

// キーボードを閉じるためのヘルパー拡張
extension View {
    func hideKeyboard() {
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }
}

#Preview {
    ContentView()
}
