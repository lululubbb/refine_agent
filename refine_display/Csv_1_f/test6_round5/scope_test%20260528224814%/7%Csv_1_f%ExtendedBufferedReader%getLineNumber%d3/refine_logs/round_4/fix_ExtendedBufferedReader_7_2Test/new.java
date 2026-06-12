package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_2Test {

    @Test
    void testGetLineNumber_initialValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testGetLineNumber_afterReading() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        reader.readLine(); // Simulate reading a line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineNumber);
    }

    @Test
    void testGetLineNumber_multipleReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2\nline3"));
        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testGetLineNumber_noReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testGetLineNumber_boundaryCase() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber); // No lines read
    }

    @Test
    void testGetLineNumber_singleEmptyLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("\n"));
        reader.readLine(); // Read the empty line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineNumber); // Should count the empty line as a valid line
    }

    @Test
    void testGetLineNumber_multipleEmptyLines() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("\n\n\n"));
        reader.readLine(); // Read first empty line
        reader.readLine(); // Read second empty line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber); // Should count the first two empty lines
    }

    @Test
    void testGetLineNumber_afterReadingAllLines() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber); // All lines read
    }

    @Test
    void testRead() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        int result = reader.read();
        Assertions.assertEquals('l', result); // First character of "line1"
    }

    @Test
    void testReadAgain() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1"));
        reader.read(); // Read first character
        int result = reader.read(); // Read again to get the second character
        Assertions.assertEquals('i', result); // Second character of "line1"
    }

    @Test
    void testReadCharArray() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1"));
        char[] buf = new char[5];
        int result = reader.read(buf, 0, 5);
        Assertions.assertEquals(5, result); // Should read 5 characters
        Assertions.assertEquals("line1", new String(buf)); // Check if read correctly
    }

    @Test
    void testLookAhead() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("line1\nline2"));
        int result = reader.lookAhead();
        Assertions.assertEquals('l', result); // Look ahead should return the first character
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}