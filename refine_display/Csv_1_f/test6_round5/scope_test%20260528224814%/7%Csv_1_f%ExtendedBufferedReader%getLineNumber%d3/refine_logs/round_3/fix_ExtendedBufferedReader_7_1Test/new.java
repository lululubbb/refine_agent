package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_1Test {

    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        extendedBufferedReader = new ExtendedBufferedReader(new StringReader("line1\nline2\nline3"));
    }

    @Test
    void testgetLineNumber_initialState() throws Exception {
        int lineNumber = invokeGetLineNumber();
        Assertions.assertEquals(0, lineNumber, "Initial line number should be 0");
    }

    @Test
    void testgetLineNumber_afterReadingLines() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        int lineNumber = invokeGetLineNumber();
        Assertions.assertEquals(1, lineNumber, "Line number should be 1 after reading first line");
        
        extendedBufferedReader.readLine(); // Read second line
        lineNumber = invokeGetLineNumber();
        Assertions.assertEquals(2, lineNumber, "Line number should be 2 after reading second line");
        
        extendedBufferedReader.readLine(); // Read third line
        lineNumber = invokeGetLineNumber();
        Assertions.assertEquals(3, lineNumber, "Line number should be 3 after reading third line");
    }

    @Test
    void testgetLineNumber_afterReadingAllLines() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line
        extendedBufferedReader.readLine(); // Read third line
        int lineNumber = invokeGetLineNumber();
        Assertions.assertEquals(3, lineNumber, "Line number should be 3 after reading all lines");
        
        extendedBufferedReader.readLine(); // Attempt to read beyond the last line
        lineNumber = invokeGetLineNumber();
        Assertions.assertEquals(3, lineNumber, "Line number should remain 3 after reading beyond the last line");
    }

    @Test
    void testgetLineNumber_emptyReader() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        int lineNumber = invokeGetLineNumber(emptyReader);
        Assertions.assertEquals(0, lineNumber, "Initial line number should be 0 for an empty reader");
        
        emptyReader.readLine(); // Attempt to read from an empty reader
        lineNumber = invokeGetLineNumber(emptyReader);
        Assertions.assertEquals(0, lineNumber, "Line number should remain 0 after reading from an empty reader");
    }

    @Test
    void testRead() throws Exception {
        int charRead = extendedBufferedReader.read();
        Assertions.assertEquals('l', charRead, "First character read should be 'l'");
        Assertions.assertEquals(0, invokeGetLineNumber(), "Line number should remain 0 after reading a character");
    }

    @Test
    void testReadAgain() throws Exception {
        int charRead = extendedBufferedReader.read();
        Assertions.assertEquals('l', charRead, "First character read should be 'l'");
        int nextCharRead = extendedBufferedReader.readAgain();
        Assertions.assertEquals('i', nextCharRead, "Next character read should be 'i'");
    }

    @Test
    void testReadWithBuffer() throws Exception {
        char[] buffer = new char[10];
        int charsRead = extendedBufferedReader.read(buffer, 0, 10);
        Assertions.assertEquals(10, charsRead, "Should read 10 characters");
        Assertions.assertEquals("line1\nline2", new String(buffer, 0, charsRead), "Buffer content should match expected string");
    }

    @Test
    void testLookAhead() throws Exception {
        int lookAheadChar = extendedBufferedReader.lookAhead();
        Assertions.assertEquals('l', lookAheadChar, "Look ahead should return 'l' from 'line1'");
    }

    private int invokeGetLineNumber() throws Exception {
        return invokeGetLineNumber(this.extendedBufferedReader);
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}