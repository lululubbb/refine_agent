package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_8_5Test {

    @Test
    public void testvalues_normalCase() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] inputValues = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_singleElement() throws Exception {
        String[] inputValues = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_withMapping() throws Exception {
        String[] inputValues = {"valueA", "valueB"};
        Map<String, Integer> mapping = Collections.singletonMap("key", 0);
        CSVRecord csvRecord = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_withNullValues() throws Exception {
        String[] inputValues = {null, "valueB"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_largeArray() throws Exception {
        String[] inputValues = new String[1000];
        Arrays.fill(inputValues, "value");
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_boundaryCase() throws Exception {
        String[] inputValues = {null, "", "valueC"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(inputValues, mapping, null, 1);

        String[] result = invokeValues(csvRecord);
        Assertions.assertArrayEquals(inputValues, result);
    }

    private String[] invokeValues(CSVRecord csvRecord) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        return (String[]) method.invoke(csvRecord);
    }
}