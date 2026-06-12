package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_6Test {

    @Test
    void testGetLineNumber_initialState() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));

        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testGetLineNumber_afterReadingLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("First line\nSecond line"));

        reader.readLine(); // Simulate reading a line
        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(1, lineNumber); // Expect 1 after reading the first line
    }

    @Test
    void testGetLineNumber_afterMultipleReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));

        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(2, lineNumber); // Expect 2 after reading two lines
    }

    @Test
    void testGetLineNumber_afterReadingAllLines() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));

        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        reader.readLine(); // Read third line
        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(3, lineNumber); // Expect 3 after reading all three lines
    }

    @Test
    void testGetLineNumber_afterReadingEmptyReader() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));

        int lineNumber = invokeGetLineNumber(reader);

        Assertions.assertEquals(0, lineNumber); // Expect 0 for an empty reader
    }

    @Test
    void testRead_singleCharacter() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("A"));

        int result = reader.read();
        
        Assertions.assertEquals('A', result); // Expect 'A' to be read
        Assertions.assertEquals(1, invokeGetLineNumber(reader)); // Expect line number to be 1
    }

    @Test
    void testReadAgain() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2"));

        reader.read(); // Read first character
        reader.read(); // Read second character
        int result = reader.readAgain(); // Simulate readAgain method

        Assertions.assertEquals('i', result); // Expect 'i' to be read next
        Assertions.assertEquals(1, invokeGetLineNumber(reader)); // Expect line number to be 1
    }

    @Test
    void testRead_withBuffer() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Buffered line"));

        char[] buffer = new char[8];
        int result = reader.read(buffer, 0, buffer.length);

        Assertions.assertEquals(8, result); // Expect to read 8 characters
        Assertions.assertEquals("Bufferd", new String(buffer, 0, result)); // Expect buffer to contain "Bufferd"
    }

    @Test
    void testLookAhead() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Look ahead"));

        int result = reader.lookAhead(); // Simulate lookAhead method

        Assertions.assertEquals('L', result); // Expect 'L' to be looked ahead
        Assertions.assertEquals(0, invokeGetLineNumber(reader)); // Expect line number to remain 0
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}