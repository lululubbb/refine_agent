package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_8_2Test {

    @Test
    public void testvalues_normalCase() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        String[] result = invokeValuesMethod(record);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] inputValues = {};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        String[] result = invokeValuesMethod(record);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_singleElement() throws Exception {
        String[] inputValues = {"singleValue"};
        CSVRecord record = new CSVRecord(inputValues, new HashMap<>(), null, 1);
        String[] result = invokeValuesMethod(record);
        Assertions.assertArrayEquals(inputValues, result);
    }

    private String[] invokeValuesMethod(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        return (String[]) method.invoke(record);
    }
}