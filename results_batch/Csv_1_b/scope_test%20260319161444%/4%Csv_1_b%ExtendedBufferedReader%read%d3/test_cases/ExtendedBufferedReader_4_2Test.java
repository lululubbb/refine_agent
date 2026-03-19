import java.io.Reader;
import java.io.IOException;
import java.io.BufferedReader;
package package org.apache.commons.csv;;
class ExtendedBufferedReader_4_2Test {

    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        Reader reader = new Reader() {
            private final char[] data = "line1\r\nline2\nline3\rline4".toCharArray();
            private int pos = 0;

            @Override
            public int read(char[] cbuf, int off, int len) {
                if (pos >= data.length) {
                    return -1;
                }
                int charsToRead = Math.min(len, data.length - pos);
                System.arraycopy(data, pos, cbuf, off, charsToRead);
                pos += charsToRead;
                return charsToRead;
            }

            @Override
            public void close() {
            }
        };
        extendedBufferedReader = new ExtendedBufferedReader(reader);
    }

    @Test
    void testRead_normalPath_countsLinesCorrectly() throws Exception {
        char[] buffer = new char[20];
        int readCount = extendedBufferedReader.read(buffer, 0, 20);
        assertEquals(20, readCount);

        // Reflectively access lineCounter and lastChar fields
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCounter = (int) lineCounterField.get(extendedBufferedReader);

        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        int lastChar = (int) lastCharField.get(extendedBufferedReader);

        // Input string: "line1\r\nline2\nline3\rline4"
        // Lines: 4
        // Counting CRLF as one line break, CR alone, LF alone
        assertEquals(4, lineCounter);
        assertEquals('4', lastChar);
    }

    @Test
    void testRead_zeroLength_returnsZeroAndDoesNotChangeState() throws Exception {
        char[] buffer = new char[10];
        setPrivateField(extendedBufferedReader, "lineCounter", 5);
        setPrivateField(extendedBufferedReader, "lastChar", 'X');

        int result = extendedBufferedReader.read(buffer, 0, 0);
        assertEquals(0, result);

        int lineCounterAfter = (int) getPrivateField(extendedBufferedReader, "lineCounter");
        int lastCharAfter = (int) getPrivateField(extendedBufferedReader, "lastChar");

        assertEquals(5, lineCounterAfter);
        assertEquals('X', lastCharAfter);
    }

    @Test
    void testRead_endOfStream_setsLastCharToEndOfStream() throws Exception {
        // Read all data first
        char[] buffer = new char[50];
        while (extendedBufferedReader.read(buffer, 0, buffer.length) != -1) {
            // consume all
        }
        // Now reading again should return -1 and set lastChar to END_OF_STREAM
        int result = extendedBufferedReader.read(buffer, 0, 10);
        assertEquals(-1, result);

        int lastChar = (int) getPrivateField(extendedBufferedReader, "lastChar");
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, lastChar);
    }

    @Test
    void testRead_negativeLength_throwsIndexOutOfBoundsException() {
        char[] buffer = new char[10];
        assertThrows(IndexOutOfBoundsException.class, () -> extendedBufferedReader.read(buffer, 0, -1));
    }

    @Test
    void testRead_offsetTooLarge_throwsIndexOutOfBoundsException() {
        char[] buffer = new char[5];
        assertThrows(IndexOutOfBoundsException.class, () -> extendedBufferedReader.read(buffer, 6, 1));
    }

    // Helper methods for reflection

    private Object getPrivateField(Object obj, String fieldName) throws Exception {
        Field f = ExtendedBufferedReader.class.getDeclaredField(fieldName);
        f.setAccessible(true);
        return f.get(obj);
    }

    private void setPrivateField(Object obj, String fieldName, Object value) {
        try {
            Field f = ExtendedBufferedReader.class.getDeclaredField(fieldName);
            f.setAccessible(true);
            f.set(obj, value);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}