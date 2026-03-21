package org.apache.commons.csv;
import java.io.BufferedReader;
import org.apache.commons.csv.ExtendedBufferedReader;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Field;

import static org.junit.jupiter.api.Assertions.*;

class ExtendedBufferedReader_3_1Test {

    ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("test"));
    }

    @Test
    void testReadAgain_initialValue() throws Exception {
        // lastChar defaults to UNDEFINED (-2)
        int result = reader.readAgain();
        assertEquals(-2, result);
    }

    @Test
    void testReadAgain_afterSettingLastCharPositive() throws Exception {
        setLastChar(10);
        int result = reader.readAgain();
        assertEquals(10, result);
    }

    @Test
    void testReadAgain_afterSettingLastCharZero() throws Exception {
        setLastChar(0);
        int result = reader.readAgain();
        assertEquals(0, result);
    }

    @Test
    void testReadAgain_afterSettingLastCharNegativeButNotConstants() throws Exception {
        setLastChar(-5);
        int result = reader.readAgain();
        assertEquals(-5, result);
    }

    @Test
    void testReadAgain_afterSettingLastCharEndOfStream() throws Exception {
        setLastChar(ExtendedBufferedReader.END_OF_STREAM);
        int result = reader.readAgain();
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    private void setLastChar(int value) throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, value);
    }
}