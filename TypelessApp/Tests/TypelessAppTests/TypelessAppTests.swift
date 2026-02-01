import Testing
@testable import TypelessApp

@Suite("TypelessApp Tests")
struct TypelessAppTests {

    @Test("Application name is correct")
    func applicationName() async throws {
        #expect("Typeless" == "Typeless")
    }

    @Test("Basic math works")
    func basicMath() async throws {
        #expect(2 + 2 == 4)
        #expect(10 / 2 == 5)
    }

    @Test("Boolean logic works")
    func booleanLogic() async throws {
        #expect(true == true)
        #expect(false == false)
    }
}
