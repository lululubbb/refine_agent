package org.apache.commons.csv;
import java.io.BufferedReader;
import org.apache.commons.csv.ExtendedBufferedReader;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

import static org.junit.jupiter.api.Assertions.*;

class ExtendedBufferedReader_2_1Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        // Initialize with a Reader that contains multiple lines
        reader = new ExtendedBufferedReader(new StringReader("line1\nline2\nline3"));
    }

    @Test
    void testRead_normalPath_incrementsLineCounterOnNewline() throws IOException {
        int c;
        int newlineCount = 0;
        while ((c = reader.read()) != -1) {
            if (c == '\n') {
                newlineCount++;
            }
        }
        // lineCounter private but we can check indirectly by counting newlines read
        // Since the input has 2 newlines, lineCounter should be 2
        // Use reflection to access private lineCounter
        int lineCounter = getPrivateLineCounter(reader);
        assertEquals(newlineCount, lineCounter);
    }

    @Test
    void testRead_emptyStream_returnsEndOfStreamImmediately() throws IOException {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        int result = emptyReader.read();
        assertEquals(-1, result);
        // lineCounter should be 0
        int lineCounter = getPrivateLineCounter(emptyReader);
        assertEquals(0, lineCounter);
    }

    @Test
    void testRead_onlyNewlineCharacters_incrementsLineCounterCorrectly() throws IOException {
        ExtendedBufferedReader newlineReader = new ExtendedBufferedReader(new StringReader("\n\n\n"));
        int count = 0;
        int c;
        while ((c = newlineReader.read()) != -1) {
            count++;
        }
        // 3 characters read, all newlines
        assertEquals(3, count);
        int lineCounter = getPrivateLineCounter(newlineReader);
        assertEquals(3, lineCounter);
    }

    @Test
    void testRead_afterEndOfStream_returnsEndOfStream() throws IOException {
        ExtendedBufferedReader singleCharReader = new ExtendedBufferedReader(new StringReader("a"));
        int first = singleCharReader.read();
        assertEquals('a', first);
        int second = singleCharReader.read();
        assertEquals(-1, second);
        int third = singleCharReader.read();
        assertEquals(-1, third);
    }

    @Test
    void testRead_throwsIOException_whenUnderlyingReaderThrows() {
        Reader failingReader = new Reader() {
            @Override
            public int read(char[] cbuf, int off, int len) throws IOException {
                throw new IOException("Forced failure");
            }

            @Override
            public void close() throws IOException {
            }
        };
        ExtendedBufferedReader failingExtendedReader = new ExtendedBufferedReader(failingReader);
        IOException thrown = assertThrows(IOException.class, failingExtendedReader::read);
        assertEquals("Forced failure", thrown.getMessage());
    }

    private int getPrivateLineCounter(ExtendedBufferedReader reader) {
        try {
            var field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
            field.setAccessible(true);
            return field.getInt(reader);
        } catch (NoSuchFieldException | IllegalAccessException e) {
            fail("Reflection failed to access lineCounter: " + e.getMessage());
            return -1;
        }
    }
}