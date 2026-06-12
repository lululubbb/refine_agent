package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_3_4Test {

    @Test
    void testReadAgain_initialState() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        invokeSetLastChar(reader, ExtendedBufferedReader.UNDEFINED);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, reader.readAgain());
    }

    @Test
    void testReadAgain_afterSettingLastChar() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        invokeSetLastChar(reader, 5);
        Assertions.assertEquals(5, reader.readAgain());
    }

    @Test
    void testReadAgain_afterSettingLastCharToEndOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        invokeSetLastChar(reader, ExtendedBufferedReader.END_OF_STREAM);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.readAgain());
    }

    private void invokeSetLastChar(ExtendedBufferedReader reader, int value) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("setLastChar", int.class);
        method.setAccessible(true);
        method.invoke(reader, value);
    }
}