import java.io.Reader;
import java.io.IOException;
import java.io.BufferedReader;
package package org.apache.commons.csv;;
class ExtendedBufferedReader_4_1Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new Reader() {
            private final char[] content = "line1\r\nline2\nline3\rline4".toCharArray();
            private int pos = 0;

            @Override
            public int read(char[] cbuf, int off, int len) {
                if (pos >= content.length) {
                    return -1;
                }
                int charsToRead = Math.min(len, content.length - pos);
                System.arraycopy(content, pos, cbuf, off, charsToRead);
                pos += charsToRead;
                return charsToRead;
            }

            @Override
            public void close() {
            }
        });
    }

    @Test
    void testread_normalPath_readsCharsAndUpdatesLineCounter() throws IOException {
        char[] buffer = new char[20];
        int readLen = reader.read(buffer, 0, 20);
        assertTrue(readLen > 0);
        String readStr = new String(buffer, 0, readLen);
        assertTrue(readStr.contains("line1") && readStr.contains("line2") && readStr.contains("line3") && readStr.contains("line4"));
        // lineCounter should be 3 for \r\n, \n, \r line breaks in the input
        int lineNumber = reader.getLineNumber();
        assertEquals(3, lineNumber);
    }

    @Test
    void testread_lengthZero_returnsZeroWithoutReading() throws IOException {
        char[] buffer = new char[10];
        int result = reader.read(buffer, 0, 0);
        assertEquals(0, result);
    }

    @Test
    void testread_negativeLength_throwsIndexOutOfBoundsException() {
        char[] buffer = new char[10];
        assertThrows(IndexOutOfBoundsException.class, () -> reader.read(buffer, 0, -1));
    }

    @Test
    void testread_offsetAndLengthBoundaryConditions() throws IOException {
        char[] buffer = new char[10];
        // offset at buffer.length - 1, length 1
        int result = reader.read(buffer, buffer.length - 1, 1);
        assertTrue(result == 1 || result == -1);
    }

    @Test
    void testread_endOfStream_setsLastCharToEndOfStream() throws IOException {
        char[] buffer = new char[100];
        // read all content first
        while (reader.read(buffer, 0, buffer.length) != -1) {
            // continue reading
        }
        // Now at end of stream, next read returns -1 and sets lastChar to END_OF_STREAM
        int result = reader.read(buffer, 0, buffer.length);
        assertEquals(-1, result);

        // Using reflection to verify private field lastChar == END_OF_STREAM
        try {
            java.lang.reflect.Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
            lastCharField.setAccessible(true);
            int lastChar = lastCharField.getInt(reader);
            assertEquals(ExtendedBufferedReader.END_OF_STREAM, lastChar);
        } catch (NoSuchFieldException | IllegalAccessException e) {
            fail("Reflection failed to access lastChar field");
        }
    }
}